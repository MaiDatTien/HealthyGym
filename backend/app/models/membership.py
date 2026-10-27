"""Models cho VÒNG ĐỜI HỢP ĐỒNG HỘI VIÊN (Membership Lifecycle).

Bao gồm:
    MembershipContract  : hợp đồng gói tập (nguồn sự thật về quyền lợi thẻ)
    FreezeRequest       : bảo lưu (7-60 ngày/năm, chỉ gói >= 3 tháng)
    TransferRequest     : chuyển nhượng gói tập giữa 2 hội viên
    UpgradeRequest      : nâng cấp gói với khấu trừ prorated
    Installment         : công nợ / trả góp, tự khóa thẻ khi quá hạn
    Lead                : khách tập thử + pipeline CRM cho Sale
    TrialPass           : vé tập thử có QR + xác thực OTP chống lạm dụng
    MemberWallet        : ví trả trước (POS, dịch vụ)
    WalletTransaction   : sổ cái giao dịch ví
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    ForeignKey, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base
from app.models.interaction import now_local


# --------------------------------------------------------------------------
# ENUM DẠNG HẰNG SỐ (theo convention sẵn có của dự án: String + hằng số)
# --------------------------------------------------------------------------
class ContractStatus:
    PENDING = "pending"        # chờ thanh toán / kích hoạt
    ACTIVE = "active"
    FROZEN = "frozen"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    TRANSFERRED = "transferred"
    ALL = (PENDING, ACTIVE, FROZEN, EXPIRED, CANCELLED, TRANSFERRED)


class TierLevel:
    STANDARD = "standard"      # 1 chi nhánh
    GOLD = "gold"              # toàn chuỗi + tiện ích
    VIP = "vip"                # toàn chuỗi + tủ cố định + xông hơi + guest pass
    ALL = (STANDARD, GOLD, VIP)


class TimeWindow:
    OFF_PEAK = "off_peak"      # chỉ check-in 09:00 - 16:00
    FULL_TIME = "full_time"
    ALL = (OFF_PEAK, FULL_TIME)


class LeadStage:
    NEW = "new"                                  # mới đăng ký
    SCHEDULED = "scheduled"                      # đã hẹn lịch
    FIRST_VISIT = "first_visit"                  # đã đến tập buổi 1
    INBODY_CONSULTED = "inbody_consulted"        # đã đo InBody & tư vấn AI
    WON = "won"                                  # chốt gói thành công
    LOST = "lost"                                # từ chối
    ALL = (NEW, SCHEDULED, FIRST_VISIT, INBODY_CONSULTED, WON, LOST)


class PaymentStatus:
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    ALL = (UNPAID, PARTIAL, PAID, OVERDUE)


# --------------------------------------------------------------------------
# HỢP ĐỒNG HỘI VIÊN
# --------------------------------------------------------------------------
class MembershipContract(Base):
    """Hợp đồng gói tập — mỗi lần mua/gia hạn/nâng cấp sinh 1 hợp đồng mới.

    Tách khỏi bảng `members` để giữ được toàn bộ lịch sử giao dịch tài chính
    và phục vụ tính prorated khi nâng cấp gói.
    """

    __tablename__ = "membership_contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_code = Column(String(40), unique=True, index=True, nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)

    # --- Điều khoản thương mại ---
    tier = Column(String(20), default=TierLevel.STANDARD, index=True)
    time_window = Column(String(20), default=TimeWindow.FULL_TIME, index=True)
    start_date = Column(Date, default=date.today, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_days = Column(Integer, nullable=False)

    # --- Tài chính ---
    list_price = Column(Float, default=0)          # giá niêm yết
    discount_amount = Column(Float, default=0)
    prorated_credit = Column(Float, default=0)     # khấu trừ từ gói cũ khi nâng cấp
    final_price = Column(Float, default=0)
    paid_amount = Column(Float, default=0)
    payment_status = Column(String(20), default=PaymentStatus.UNPAID, index=True)

    # --- Trạng thái & vòng đời ---
    status = Column(String(20), default=ContractStatus.PENDING, index=True)
    freeze_days_used = Column(Integer, default=0)   # đã dùng trong năm (tối đa 60)
    is_renewal = Column(Boolean, default=False)
    previous_contract_id = Column(Integer, ForeignKey("membership_contracts.id"), nullable=True)
    upgraded_from_plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=True)

    # --- Tiện ích đi kèm theo hạng thẻ ---
    includes_locker = Column(Boolean, default=False)
    includes_towel = Column(Boolean, default=True)
    includes_sauna = Column(Boolean, default=False)
    guest_passes_month = Column(Integer, default=0)

    owner_type = Column(String(20), default="individual")  # individual | couple | group
    group_code = Column(String(40), nullable=True, index=True)  # combo nhóm

    sold_by = Column(String(150), nullable=True)   # nhân viên Sale chốt hợp đồng
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local)
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(Text, nullable=True)

    member = relationship("Member", foreign_keys=[member_id])
    plan = relationship("MembershipPlan", foreign_keys=[plan_id])
    branch = relationship("Branch")
    installments = relationship(
        "Installment", back_populates="contract", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_contract_member_status", "member_id", "status"),
        Index("ix_contract_end_date", "end_date", "status"),
    )

    @property
    def days_remaining(self) -> int:
        """Số ngày còn lại của hợp đồng."""
        return max(0, (self.end_date - date.today()).days)

    @property
    def prorated_value(self) -> float:
        """Giá trị còn lại theo số ngày chưa sử dụng — dùng cho nâng cấp gói."""
        if self.duration_days <= 0:
            return 0.0
        return round(self.final_price * (self.days_remaining / self.duration_days), 0)


# --------------------------------------------------------------------------
# BẢO LƯU
# --------------------------------------------------------------------------
class FreezeRequest(Base):
    """Yêu cầu bảo lưu thẻ tập.

    Quy tắc: chỉ gói >= 3 tháng, mỗi lần 7-60 ngày, tổng không quá 60 ngày/năm.
    """

    __tablename__ = "freeze_requests"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("membership_contracts.id"), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)

    status = Column(String(20), default="pending", index=True)  # pending|approved|rejected|completed
    approved_by = Column(String(150), nullable=True)
    old_end_date = Column(Date, nullable=True)
    new_end_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=now_local)
    processed_at = Column(DateTime, nullable=True)

    member = relationship("Member")
    contract = relationship("MembershipContract")


# --------------------------------------------------------------------------
# CHUYỂN NHƯỢNG
# --------------------------------------------------------------------------
class TransferRequest(Base):
    """Chuyển nhượng thời hạn gói tập còn lại giữa 2 hội viên."""

    __tablename__ = "transfer_requests"

    id = Column(Integer, primary_key=True, index=True)
    from_member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    from_contract_id = Column(Integer, ForeignKey("membership_contracts.id"), nullable=False)
    to_member_id = Column(Integer, ForeignKey("members.id"), nullable=True, index=True)
    to_full_name = Column(String(255), nullable=False)
    to_phone = Column(String(30), nullable=False)
    to_email = Column(String(255), nullable=True)

    transfer_fee = Column(Float, default=300000)
    remaining_days = Column(Integer, default=0)
    status = Column(String(20), default="pending", index=True)  # pending|approved|rejected|completed
    new_contract_id = Column(Integer, ForeignKey("membership_contracts.id"), nullable=True)
    approved_by = Column(String(150), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local)
    processed_at = Column(DateTime, nullable=True)

    from_member = relationship("Member", foreign_keys=[from_member_id])
    to_member = relationship("Member", foreign_keys=[to_member_id])


# --------------------------------------------------------------------------
# NÂNG CẤP GÓI
# --------------------------------------------------------------------------
class UpgradeRequest(Base):
    """Nâng cấp gói tập với khấu trừ giá trị còn lại (prorated billing)."""

    __tablename__ = "upgrade_requests"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    old_contract_id = Column(Integer, ForeignKey("membership_contracts.id"), nullable=False)
    new_plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=False)

    old_prorated_value = Column(Float, default=0)   # giá trị còn lại của gói cũ
    new_plan_price = Column(Float, default=0)
    amount_due = Column(Float, default=0)           # số tiền phải trả thêm
    status = Column(String(20), default="pending", index=True)
    new_contract_id = Column(Integer, ForeignKey("membership_contracts.id"), nullable=True)
    approved_by = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=now_local)
    processed_at = Column(DateTime, nullable=True)

    member = relationship("Member")


# --------------------------------------------------------------------------
# CÔNG NỢ / TRẢ GÓP
# --------------------------------------------------------------------------
class Installment(Base):
    """Lịch thanh toán trả góp / đặt cọc giữ chỗ."""

    __tablename__ = "installments"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("membership_contracts.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    sequence = Column(Integer, default=1)           # kỳ thứ mấy
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    paid_amount = Column(Float, default=0)
    paid_at = Column(DateTime, nullable=True)
    status = Column(String(20), default=PaymentStatus.UNPAID, index=True)
    method = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local)

    contract = relationship("MembershipContract", back_populates="installments")


# --------------------------------------------------------------------------
# LEADS (KHÁCH TẬP THỬ) & CRM
# --------------------------------------------------------------------------
class Lead(Base):
    """Khách tập thử — pipeline CRM cho Lễ tân/Sale."""

    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    source = Column(String(80), default="website")   # website|walk_in|referral|facebook
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)

    stage = Column(String(30), default=LeadStage.NEW, index=True)
    trial_pass_id = Column(Integer, ForeignKey("trial_passes.id"), nullable=True)
    interested_plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=True)
    assigned_to = Column(String(150), nullable=True, index=True)   # Sale phụ trách
    converted_member_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    converted_contract_id = Column(Integer, ForeignKey("membership_contracts.id"), nullable=True)

    first_visit_at = Column(DateTime, nullable=True)
    inbody_done_at = Column(DateTime, nullable=True)
    consultation_note = Column(Text, nullable=True)
    lost_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=now_local)
    updated_at = Column(DateTime, default=now_local, onupdate=now_local)

    trial_pass = relationship("TrialPass", foreign_keys=[trial_pass_id])


class TrialPass(Base):
    """Vé tập thử miễn phí kèm QR và xác thực OTP chống 1 người đăng ký nhiều lần."""

    __tablename__ = "trial_passes"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)

    qr_code = Column(String(60), unique=True, index=True, nullable=False)
    days = Column(Integer, default=7)
    start_date = Column(Date, default=date.today)
    end_date = Column(Date, nullable=False)

    otp_code = Column(String(10), nullable=True)
    otp_verified = Column(Boolean, default=False, index=True)
    otp_expires_at = Column(DateTime, nullable=True)
    otp_attempts = Column(Integer, default=0)

    status = Column(String(20), default="pending", index=True)  # pending|active|used|expired
    visits_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=now_local)


# --------------------------------------------------------------------------
# VÍ TRẢ TRƯỚC & SỔ CÁI GIAO DỊCH
# --------------------------------------------------------------------------
class MemberWallet(Base):
    """Ví trả trước của hội viên — dùng cho POS, thuê tủ, dịch vụ."""

    __tablename__ = "member_wallets"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), unique=True, nullable=False)
    balance = Column(Float, default=0)
    total_topup = Column(Float, default=0)
    total_spent = Column(Float, default=0)
    updated_at = Column(DateTime, default=now_local, onupdate=now_local)

    member = relationship("Member")


class WalletTransaction(Base):
    """Sổ cái giao dịch ví — mọi biến động số dư đều ghi ở đây."""

    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("member_wallets.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)          # dương = nạp, âm = chi
    balance_after = Column(Float, nullable=False)
    kind = Column(String(30), default="topup", index=True)  # topup|purchase|refund|penalty|reward
    reference = Column(String(80), nullable=True)   # mã đơn POS / phiếu phạt
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local, index=True)