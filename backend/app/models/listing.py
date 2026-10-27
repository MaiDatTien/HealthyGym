from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base

class Branch(Base):
    __tablename__ = "branches"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    phone = Column(String(50), nullable=True)
    opening_hours = Column(String(100), default="06:00 - 22:00")
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    facilities = relationship("Facility", back_populates="branch")
    classes = relationship("GymClass", back_populates="branch")

class Facility(Base):
    __tablename__ = "facilities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="Cardio")
    quantity = Column(Integer, default=1)
    status = Column(String(50), default="Hoạt động tốt")
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)

    # --- Vòng đời thiết bị ---
    #: active (tốt) | maintenance (đang bảo trì) | out_of_order (ngưng dùng)
    lifecycle_status = Column(String(20), default="active", index=True)
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    purchase_date = Column(Date, nullable=True)
    warranty_until = Column(Date, nullable=True)
    #: Chu kỳ bảo trì định kỳ (ngày)
    maintenance_cycle_days = Column(Integer, default=90)
    last_maintenance_date = Column(Date, nullable=True)
    next_maintenance_date = Column(Date, nullable=True, index=True)
    location_note = Column(String(255), nullable=True)

    branch = relationship("Branch", back_populates="facilities")
    machine_qrs = relationship("MachineQR", back_populates="facility", cascade="all, delete-orphan")


class MembershipPlan(Base):
    __tablename__ = "membership_plans"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    duration_days = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    benefits = Column(Text, nullable=True)
    includes_pt = Column(Boolean, default=False)
    is_popular = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # --- Cấu hình hạng thẻ & khung giờ ---
    plan_kind = Column(String(20), default="membership")  # membership | pt_package | service
    tier = Column(String(20), default="standard", index=True)  # standard | gold | vip
    time_window = Column(String(20), default="full_time")      # off_peak | full_time
    off_peak_start_hour = Column(Integer, default=9)           # 09:00
    off_peak_end_hour = Column(Integer, default=16)            # 16:00
    branch_scope = Column(String(20), default="single")        # single | chain

    # --- Tiện ích theo hạng ---
    includes_locker = Column(Boolean, default=False)
    includes_towel = Column(Boolean, default=True)
    includes_sauna = Column(Boolean, default=False)
    guest_passes_month = Column(Integer, default=0)

    # --- Quy tắc bảo lưu ---
    freeze_allowed = Column(Boolean, default=True)
    max_freeze_days = Column(Integer, default=60)
    min_freeze_days = Column(Integer, default=7)
    min_duration_for_freeze = Column(Integer, default=90)   # gói >= 3 tháng

    # --- Quy tắc chuyển nhượng ---
    transfer_allowed = Column(Boolean, default=True)
    transfer_fee = Column(Float, default=300000)
    min_days_for_transfer = Column(Integer, default=30)

    # --- Kèm gói PT (nếu là combo) ---
    included_pt_sessions = Column(Integer, default=0)      # số buổi PT tặng kèm
    min_commitment_months = Column(Integer, default=1)

class GymClass(Base):
    __tablename__ = "gym_classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="Yoga")
    schedule_time = Column(String(255), nullable=False)
    room = Column(String(100), default="Studio A")
    capacity = Column(Integer, default=20)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    description = Column(Text, nullable=True)

    trainer = relationship("Trainer", back_populates="classes")
    branch = relationship("Branch", back_populates="classes")
    bookings = relationship("Booking", back_populates="gym_class", cascade="all, delete-orphan")

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    category = Column(String(100), default="Dinh dưỡng & Tập luyện")
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
