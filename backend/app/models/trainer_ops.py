"""Models cho NGHIỆP VỤ HUẤN LUYỆN VIÊN (PT) & CHỐNG GIAN LẬN.

Bao gồm:
    PTPackage          : gói tập PT tính theo SỐ BUỔI (khác gói hội viên theo ngày)
    PTPackagePurchase  : hội viên mua gói PT, theo dõi số buổi còn lại
    TrainerShift       : ca làm việc của PT trong tuần
    PTBurnConfirmation : xác nhận kép trừ buổi (chống PT tự bấm hoàn thành)
    TrainerChangeRequest : yêu cầu đổi PT / dạy thay
    TrainerPayroll     : bảng lương & hoa hồng PT theo tháng
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    ForeignKey, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base
from app.models.interaction import now_local


class PackageStatus:
    ACTIVE = "active"
    EXHAUSTED = "exhausted"    # hết buổi
    EXPIRED = "expired"        # hết hạn
    REFUNDED = "refunded"
    ALL = (ACTIVE, EXHAUSTED, EXPIRED, REFUNDED)


class SessionOutcome:
    COMPLETED = "completed"
    LATE_CANCEL = "late_cancel"     # hủy < 6 giờ -> trừ buổi
    NO_SHOW = "no_show"             # vắng mặt -> trừ buổi
    EARLY_CANCEL = "early_cancel"   # hủy >= 6 giờ -> hoàn buổi
    ALL = (COMPLETED, LATE_CANCEL, NO_SHOW, EARLY_CANCEL)


class PTPackage(Base):
    """Gói tập PT tính theo số buổi (12/36/50/100 buổi) kèm thời hạn sử dụng."""

    __tablename__ = "pt_packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sessions = Column(Integer, nullable=False)          # tổng số buổi
    price = Column(Float, nullable=False)
    validity_days = Column(Integer, default=180)        # thời hạn sử dụng
    price_per_session = Column(Float, default=0)
    tier = Column(String(20), default="standard")       # standard|gold|vip
    includes_inbody = Column(Boolean, default=True)
    includes_nutrition = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    @property
    def unit_price(self) -> float:
        return round(self.price / self.sessions, 0) if self.sessions else 0.0


class PTPackagePurchase(Base):
    """Hội viên mua gói PT — nguồn sự thật về số buổi còn lại."""

    __tablename__ = "pt_package_purchases"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    package_id = Column(Integer, ForeignKey("pt_packages.id"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=True, index=True)

    sessions_total = Column(Integer, nullable=False)
    sessions_used = Column(Integer, default=0)
    sessions_remaining = Column(Integer, default=0)

    price = Column(Float, default=0)
    paid_amount = Column(Float, default=0)
    start_date = Column(Date, default=date.today)
    expiry_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), default=PackageStatus.ACTIVE, index=True)

    sold_by = Column(String(150), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local)

    member = relationship("Member")
    package = relationship("PTPackage")
    trainer = relationship("Trainer")

    @property
    def days_remaining(self) -> int:
        return max(0, (self.expiry_date - date.today()).days)


class TrainerShift(Base):
    """Ca làm việc của PT — dùng để sinh khung giờ trống cho hội viên đặt."""

    __tablename__ = "trainer_shifts"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    weekday = Column(Integer, nullable=False)        # 0 = Thứ 2 ... 6 = Chủ Nhật
    start_hour = Column(Integer, nullable=False)
    end_hour = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    effective_from = Column(Date, default=date.today)
    effective_to = Column(Date, nullable=True)

    trainer = relationship("Trainer")

    __table_args__ = (
        UniqueConstraint("trainer_id", "weekday", "start_hour",
                         name="uq_shift_slot_per_trainer"),
    )


class PTBurnConfirmation(Base):
    """Cơ chế XÁC NHẬN KÉP chống gian lận trừ buổi.

    Điều kiện để trừ 1 buổi thành công:
      1. member_checked_in  — hội viên có lượt check-in cổng trong ngày
      2. member_confirmed   — hội viên quét QR / nhập OTP xác nhận cuối buổi
    Chỉ khi cả hai đều true thì buổi mới được tính (và PT mới được ghi nhận hoa hồng).
    """

    __tablename__ = "pt_burn_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("pt_bookings.id"), unique=True, nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False, index=True)
    purchase_id = Column(Integer, ForeignKey("pt_package_purchases.id"), nullable=True)

    # --- Điều kiện 1: check-in tại cổng ---
    member_checked_in = Column(Boolean, default=False)
    gate_checkin_id = Column(Integer, ForeignKey("gate_checkins.id"), nullable=True)

    # --- Điều kiện 2: hội viên xác nhận cuối buổi ---
    member_confirmed = Column(Boolean, default=False)
    confirm_method = Column(String(20), nullable=True)   # qr | otp | app_button
    otp_code = Column(String(10), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)

    # --- Kết quả ---
    outcome = Column(String(20), default="pending", index=True)
    session_deducted = Column(Boolean, default=False)
    rating = Column(Integer, nullable=True)              # 1-5 sao
    feedback = Column(Text, nullable=True)

    trainer_marked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_local)
    resolved_at = Column(DateTime, nullable=True)

    booking = relationship("PTBooking")
    trainer = relationship("Trainer")


class TrainerChangeRequest(Base):
    """Yêu cầu đổi PT hoặc gán PT dạy thay cho một buổi cụ thể."""

    __tablename__ = "trainer_change_requests"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    current_trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False)
    requested_trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=True)
    booking_id = Column(Integer, ForeignKey("pt_bookings.id"), nullable=True)

    kind = Column(String(20), default="change")   # change | substitution
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="pending", index=True)
    handled_by = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=now_local)
    resolved_at = Column(DateTime, nullable=True)

    member = relationship("Member")


class TrainerPayroll(Base):
    """Bảng lương & hoa hồng PT theo tháng."""

    __tablename__ = "trainer_payrolls"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False, index=True)
    period_year = Column(Integer, nullable=False)
    period_month = Column(Integer, nullable=False)

    base_salary = Column(Float, default=0)
    sale_commission_rate = Column(Float, default=0.10)   # % hoa hồng bán gói
    burn_fee_per_session = Column(Float, default=80000)  # thù lao mỗi buổi dạy

    packages_sold_amount = Column(Float, default=0)
    sale_commission = Column(Float, default=0)
    sessions_delivered = Column(Integer, default=0)
    delivery_commission = Column(Float, default=0)
    five_star_bonus = Column(Float, default=0)
    deductions = Column(Float, default=0)                # phạt / tạm ứng

    total_pay = Column(Float, default=0)
    status = Column(String(20), default="draft", index=True)  # draft|approved|paid
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local)

    trainer = relationship("Trainer")

    __table_args__ = (
        UniqueConstraint("trainer_id", "period_year", "period_month",
                         name="uq_payroll_per_trainer_month"),
    )