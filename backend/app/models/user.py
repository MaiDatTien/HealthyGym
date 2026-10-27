from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base


class Role:
    """6 vai trò của hệ thống (RBAC).

    `staff` được giữ lại như bí danh tương thích ngược của `receptionist`.
    """

    GUEST = "guest"
    MEMBER = "member"
    TRAINER = "trainer"
    RECEPTIONIST = "receptionist"      # Lễ tân & Tư vấn viên (Sale)
    FACILITY_MANAGER = "facility_manager"  # Quản lý cơ sở vật chất
    ADMIN = "admin"                    # Super Admin / Owner
    #: Bí danh cũ — vẫn được chấp nhận khi đăng nhập
    STAFF = "staff"

    ALL = (GUEST, MEMBER, TRAINER, RECEPTIONIST, FACILITY_MANAGER, ADMIN)

    #: Nhóm quyền vận hành (được vào khu vực quản trị)
    OPERATIONS = (RECEPTIONIST, FACILITY_MANAGER, ADMIN, STAFF)

    @classmethod
    def normalize(cls, role: str | None) -> str:
        """Chuẩn hoá vai trò cũ sang vai trò mới."""
        return cls.RECEPTIONIST if role == cls.STAFF else (role or cls.GUEST)

    @classmethod
    def labels(cls) -> dict[str, str]:
        return {
            cls.GUEST: "Khách vãng lai",
            cls.MEMBER: "Hội viên",
            cls.TRAINER: "Huấn luyện viên",
            cls.RECEPTIONIST: "Lễ tân & Tư vấn",
            cls.FACILITY_MANAGER: "Quản lý CSVC",
            cls.ADMIN: "Quản trị viên",
        }


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    #: member | trainer | receptionist | facility_manager | admin | staff (cũ)
    role = Column(String(50), default=Role.MEMBER, index=True)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    member_profile = relationship("Member", back_populates="user", uselist=False)


class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    current_plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=True)
    status = Column(String(50), default="inactive")  # active, expired, frozen, inactive
    join_date = Column(Date, default=date.today)
    expire_date = Column(Date, nullable=True)
    frozen_until = Column(Date, nullable=True)

    # --- Hồ sơ sức khỏe AI ---
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=True)

    # --- Phân loại gói & quyền lợi ---
    tier = Column(String(20), default="standard", index=True)        # standard|gold|vip
    time_window = Column(String(20), default="full_time", index=True)  # off_peak|full_time
    home_branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    has_private_locker = Column(Boolean, default=False)

    # --- Điểm thưởng (số dư nhanh, sổ cái ở loyalty_points) ---
    loyalty_points = Column(Integer, default=0)
    total_points_earned = Column(Integer, default=0)

    # --- Công nợ ---
    outstanding_debt = Column(Float, default=0)
    is_debt_blocked = Column(Boolean, default=False, index=True)

    # --- QR tĩnh định danh (QR động sinh riêng theo phiên) ---
    qr_code = Column(String(60), nullable=True)

    # --- CRM ---
    last_visit_date = Column(Date, nullable=True, index=True)
    risk_level = Column(String(20), default="low", index=True)
    referred_by_member_id = Column(Integer, ForeignKey("members.id"), nullable=True)

    emergency_contact = Column(String(255), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), default="male")
    note = Column(Text, nullable=True)

    user = relationship("User", back_populates="member_profile")
    current_plan = relationship("MembershipPlan", foreign_keys=[current_plan_id])
    home_branch = relationship("Branch", foreign_keys=[home_branch_id])
    bookings = relationship("Booking", back_populates="member", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="member", cascade="all, delete-orphan")
    checkins = relationship("CheckInLog", back_populates="member", cascade="all, delete-orphan")
    health_metrics = relationship("HealthMetric", back_populates="member", cascade="all, delete-orphan")
    ai_plans = relationship("AIPlan", back_populates="member", cascade="all, delete-orphan")
    pt_bookings = relationship("PTBooking", back_populates="member", cascade="all, delete-orphan")
    coach = relationship("Trainer", foreign_keys=[trainer_id])

    contracts = relationship(
        "MembershipContract", back_populates="member",
        foreign_keys="MembershipContract.member_id", cascade="all, delete-orphan",
    )
    wallet = relationship(
        "MemberWallet", back_populates="member", uselist=False, cascade="all, delete-orphan"
    )
    streak = relationship(
        "MemberStreak", back_populates="member", uselist=False, cascade="all, delete-orphan"
    )
    pt_purchases = relationship(
        "PTPackagePurchase", back_populates="member", cascade="all, delete-orphan"
    )
    class_bookings = relationship(
        "ClassBooking", back_populates="member", cascade="all, delete-orphan"
    )
    gate_checkins = relationship(
        "GateCheckin", back_populates="member", cascade="all, delete-orphan"
    )


class Trainer(Base):
    __tablename__ = "trainers"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    specialty = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    experience_years = Column(Integer, default=1)
    avatar_url = Column(String(500), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    rating = Column(Float, default=5.0)
    rating_count = Column(Integer, default=0)
    certifications = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    # --- Thù lao ---
    base_salary = Column(Float, default=6000000)
    burn_fee_per_session = Column(Float, default=80000)      # thù lao mỗi buổi dạy
    sale_commission_rate = Column(Float, default=0.10)       # % hoa hồng bán gói

    # --- Chuyên môn phục vụ ghép cặp tự động ---
    accepts_rehab = Column(Boolean, default=False)           # nhận học viên cần phục hồi
    max_trainees = Column(Integer, default=20)
    current_trainees = Column(Integer, default=0)

    classes = relationship("GymClass", back_populates="trainer")
    slots = relationship("TrainerSlot", back_populates="trainer", cascade="all, delete-orphan")
    pt_bookings = relationship("PTBooking", back_populates="trainer", cascade="all, delete-orphan")
    shifts = relationship("TrainerShift", back_populates="trainer", cascade="all, delete-orphan")
    payrolls = relationship("TrainerPayroll", back_populates="trainer", cascade="all, delete-orphan")