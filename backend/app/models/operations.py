"""Models cho VẬN HÀNH PHÒNG TẬP.

Bao gồm:
    ClassSchedule        : buổi học cụ thể của lớp GroupX (có ngày giờ thật)
    ClassSpot            : sơ đồ vị trí (thảm Yoga / xe Cycling) theo buổi học
    ClassBooking         : đặt chỗ lớp nhóm, gắn vị trí đã chọn
    ClassWaitlist        : danh sách chờ tự động đôn người khi có chỗ trống
    BookingPenalty       : phạt khóa quyền đặt lớp khi no-show nhiều lần
    GateCheckin          : lượt vào/ra cổng với kết quả kiểm tra nhiều điều kiện
    DynamicQRToken       : mã QR động đổi mỗi 60 giây chống mượn thẻ
    Locker               : tủ đồ (tủ ngày + tủ cố định thuê theo tháng)
    LockerAssignment     : phiếu gán tủ + khăn, theo dõi thu hồi và phạt
    Product              : hàng hóa Pro-Shop (Whey, nước, phụ kiện)
    InventoryTransaction : nhập/xuất/tồn kho
    PosOrder             : đơn bán tại quầy
    PosOrderItem         : chi tiết đơn hàng
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    ForeignKey, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base
from app.models.interaction import now_local


class ScheduleStatus:
    SCHEDULED = "scheduled"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ALL = (SCHEDULED, ONGOING, COMPLETED, CANCELLED)


class BookingStatus:
    CONFIRMED = "confirmed"
    WAITLISTED = "waitlisted"
    ATTENDED = "attended"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    ALL = (CONFIRMED, WAITLISTED, ATTENDED, NO_SHOW, CANCELLED)


class GateResult:
    GRANTED = "granted"
    DENIED_EXPIRED = "denied_expired"
    DENIED_FROZEN = "denied_frozen"
    DENIED_BRANCH = "denied_branch"
    DENIED_TIME_WINDOW = "denied_time_window"
    DENIED_DEBT = "denied_debt"
    DENIED_INACTIVE = "denied_inactive"
    ALL = (GRANTED, DENIED_EXPIRED, DENIED_FROZEN, DENIED_BRANCH,
           DENIED_TIME_WINDOW, DENIED_DEBT, DENIED_INACTIVE)


# --------------------------------------------------------------------------
# GROUP-X: LỊCH LỚP, VỊ TRÍ, ĐẶT CHỖ, DANH SÁCH CHỜ
# --------------------------------------------------------------------------
class ClassSchedule(Base):
    """Một buổi học cụ thể (lớp + ngày giờ thực tế) — khác GymClass là mẫu lặp lại."""

    __tablename__ = "class_schedules"

    id = Column(Integer, primary_key=True, index=True)
    gym_class_id = Column(Integer, ForeignKey("gym_classes.id"), nullable=False, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    studio = Column(String(100), default="Studio A")

    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    capacity = Column(Integer, default=25)
    difficulty = Column(String(20), default="intermediate")  # beginner|intermediate|advanced
    status = Column(String(20), default=ScheduleStatus.SCHEDULED, index=True)

    #: Lớp có yêu cầu chọn vị trí (Yoga thảm / Cycling xe) hay không
    requires_spot_selection = Column(Boolean, default=False)
    spot_layout = Column(String(30), default="mat")  # mat | bike | none

    substitute_trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local)

    gym_class = relationship("GymClass")
    trainer = relationship("Trainer", foreign_keys=[trainer_id])
    substitute_trainer = relationship("Trainer", foreign_keys=[substitute_trainer_id])
    spots = relationship("ClassSpot", back_populates="schedule", cascade="all, delete-orphan")
    bookings = relationship("ClassBooking", back_populates="schedule", cascade="all, delete-orphan")
    waitlist = relationship("ClassWaitlist", back_populates="schedule", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_schedule_start_status", "start_time", "status"),)


class ClassSpot(Base):
    """Vị trí trong phòng (số thảm Yoga / số xe Cycling)."""

    __tablename__ = "class_spots"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("class_schedules.id"), nullable=False, index=True)
    spot_code = Column(String(20), nullable=False)   # VD: "B12" (xe 12) hoặc "M08" (thảm 8)
    zone = Column(String(50), nullable=True)         # VD: "Hàng đầu", "Gần gương"
    is_available = Column(Boolean, default=True, index=True)

    schedule = relationship("ClassSchedule", back_populates="spots")

    __table_args__ = (
        UniqueConstraint("schedule_id", "spot_code", name="uq_spot_per_schedule"),
    )


class ClassBooking(Base):
    """Đặt chỗ lớp GroupX — giữ cả vị trí đã chọn."""

    __tablename__ = "class_bookings"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("class_schedules.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("class_spots.id"), nullable=True)

    status = Column(String(20), default=BookingStatus.CONFIRMED, index=True)
    booked_at = Column(DateTime, default=now_local)
    checked_in_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    promoted_from_waitlist = Column(Boolean, default=False)
    rating = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)

    schedule = relationship("ClassSchedule", back_populates="bookings")
    spot = relationship("ClassSpot")
    member = relationship("Member")

    __table_args__ = (
        UniqueConstraint("schedule_id", "member_id", name="uq_member_per_schedule"),
        Index("ix_classbooking_member_status", "member_id", "status"),
    )


class ClassWaitlist(Base):
    """Danh sách chờ — tự động đôn người đầu hàng khi có chỗ trống."""

    __tablename__ = "class_waitlist"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("class_schedules.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False)      # thứ tự trong hàng chờ
    status = Column(String(20), default="waiting", index=True)  # waiting|promoted|expired|cancelled
    joined_at = Column(DateTime, default=now_local)
    promoted_at = Column(DateTime, nullable=True)
    notified = Column(Boolean, default=False)

    schedule = relationship("ClassSchedule", back_populates="waitlist")
    member = relationship("Member")

    __table_args__ = (
        UniqueConstraint("schedule_id", "member_id", name="uq_waitlist_member"),
    )


class BookingPenalty(Base):
    """Phạt khóa quyền đặt lớp GroupX khi no-show nhiều lần."""

    __tablename__ = "booking_penalties"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    reason = Column(String(255), nullable=False)
    no_show_count = Column(Integer, default=0)
    blocked_from = Column(Date, default=date.today)
    blocked_until = Column(Date, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(String(150), default="system")
    created_at = Column(DateTime, default=now_local)

    member = relationship("Member")


# --------------------------------------------------------------------------
# CHECK-IN CỔNG & QR ĐỘNG
# --------------------------------------------------------------------------
class DynamicQRToken(Base):
    """Mã QR động đổi mỗi 60 giây — chống chụp màn hình cho người khác mượn thẻ."""

    __tablename__ = "dynamic_qr_tokens"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    token = Column(String(80), unique=True, index=True, nullable=False)
    issued_at = Column(DateTime, default=now_local, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False, index=True)

    member = relationship("Member")


class GateCheckin(Base):
    """Lượt vào/ra cổng — lưu đầy đủ kết quả kiểm tra nhiều điều kiện."""

    __tablename__ = "gate_checkins"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("membership_contracts.id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    trial_pass_id = Column(Integer, ForeignKey("trial_passes.id"), nullable=True)

    direction = Column(String(10), default="in", index=True)  # in | out
    result = Column(String(30), default=GateResult.GRANTED, index=True)
    reason = Column(String(255), nullable=True)

    # Kết quả từng điều kiện kiểm tra (audit trail cho lễ tân tra soát)
    checks_json = Column(Text, nullable=True)

    is_off_peak_violation = Column(Boolean, default=False)
    surcharge_amount = Column(Float, default=0)

    verified_by = Column(String(150), default="QR")
    checkin_time = Column(DateTime, default=now_local, index=True)
    checkout_time = Column(DateTime, nullable=True)

    member = relationship("Member")
    branch = relationship("Branch")

    __table_args__ = (Index("ix_gate_member_time", "member_id", "checkin_time"),)


# --------------------------------------------------------------------------
# TỦ ĐỒ & KHĂN TẬP
# --------------------------------------------------------------------------
class Locker(Base):
    """Tủ đồ: tủ dùng theo ngày hoặc tủ cố định cho thuê theo tháng."""

    __tablename__ = "lockers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)  # VD: "M105"
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    zone = Column(String(30), default="male")       # male | female | vip
    kind = Column(String(20), default="daily", index=True)  # daily | private
    is_available = Column(Boolean, default=True, index=True)
    monthly_fee = Column(Float, default=200000)     # chỉ áp dụng tủ private
    note = Column(Text, nullable=True)

    branch = relationship("Branch")


class LockerAssignment(Base):
    """Phiếu gán tủ + khăn; theo dõi thu hồi và phạt khi mất/không trả."""

    __tablename__ = "locker_assignments"

    id = Column(Integer, primary_key=True, index=True)
    locker_id = Column(Integer, ForeignKey("lockers.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    gate_checkin_id = Column(Integer, ForeignKey("gate_checkins.id"), nullable=True)

    towels_issued = Column(Integer, default=1)
    towels_returned = Column(Integer, default=0)
    key_returned = Column(Boolean, default=False)

    assigned_at = Column(DateTime, default=now_local)
    returned_at = Column(DateTime, nullable=True)
    assigned_by = Column(String(150), default="Receptionist")

    penalty_amount = Column(Float, default=0)
    penalty_reason = Column(String(255), nullable=True)
    penalty_paid = Column(Boolean, default=False)

    #: Thuê tủ cố định theo tháng
    is_monthly_rental = Column(Boolean, default=False)
    rental_start = Column(Date, nullable=True)
    rental_end = Column(Date, nullable=True)

    locker = relationship("Locker")
    member = relationship("Member")


# --------------------------------------------------------------------------
# PRO-SHOP & KHO HÀNG
# --------------------------------------------------------------------------
class ProductCategory:
    DRINK = "drink"          # nước uống
    SUPPLEMENT = "supplement"  # Whey, Pre-workout, Creatine
    ACCESSORY = "accessory"  # găng tay, đai lưng, dây kháng lực
    SERVICE = "service"      # thuê tủ, khăn, PT lẻ
    ALL = (DRINK, SUPPLEMENT, ACCESSORY, SERVICE)


class Product(Base):
    """Sản phẩm Pro-Shop — hỗ trợ bán nguyên hũ hoặc bán lẻ từng muỗng tại quầy Bar."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(30), default=ProductCategory.SUPPLEMENT, index=True)
    brand = Column(String(120), nullable=True)

    unit = Column(String(30), default="hũ")        # hũ | chai | muỗng | cái
    #: Quy cách: 1 hũ = bao nhiêu muỗng (để bán lẻ)
    servings_per_unit = Column(Integer, default=0)
    price = Column(Float, nullable=False)          # giá bán lẻ 1 đơn vị
    serving_price = Column(Float, default=0)       # giá bán lẻ 1 muỗng (nếu có)
    cost_price = Column(Float, default=0)

    stock_quantity = Column(Float, default=0)
    low_stock_threshold = Column(Float, default=5)
    expiry_date = Column(Date, nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=now_local)


class InventoryTransaction(Base):
    """Nhập/xuất/điều chỉnh tồn kho."""

    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    kind = Column(String(20), default="import", index=True)  # import|export|adjust|waste
    quantity = Column(Float, nullable=False)
    stock_after = Column(Float, default=0)
    unit_cost = Column(Float, default=0)
    reference = Column(String(80), nullable=True)
    note = Column(Text, nullable=True)
    performed_by = Column(String(150), default="system")
    created_at = Column(DateTime, default=now_local, index=True)

    product = relationship("Product")


class PosOrder(Base):
    """Đơn bán tại quầy — hỗ trợ tiền mặt, chuyển khoản và trừ ví trả trước."""

    __tablename__ = "pos_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String(40), unique=True, index=True, nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True, index=True)
    customer_name = Column(String(255), nullable=True)   # khách vãng lai

    subtotal = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    total_cost = Column(Float, default=0)
    profit = Column(Float, default=0)

    payment_method = Column(String(30), default="cash")  # cash|transfer|wallet|card
    wallet_txn_id = Column(Integer, ForeignKey("wallet_transactions.id"), nullable=True)
    status = Column(String(20), default="completed", index=True)  # completed|refunded|cancelled

    cashier = Column(String(150), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local, index=True)

    member = relationship("Member")
    items = relationship("PosOrderItem", back_populates="order", cascade="all, delete-orphan")


class PosOrderItem(Base):
    """Chi tiết đơn hàng POS."""

    __tablename__ = "pos_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("pos_orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(30), default="hũ")
    unit_price = Column(Float, nullable=False)
    cost_price = Column(Float, default=0)
    line_total = Column(Float, nullable=False)

    order = relationship("PosOrder", back_populates="items")
    product = relationship("Product")