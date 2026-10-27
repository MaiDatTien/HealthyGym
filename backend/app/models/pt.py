"""Models cho nghiệp vụ PT 1-1, bảo trì thiết bị và hồ sơ học viên của HLV."""
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base


class TrainerSlot(Base):
    """Khung giờ trống của HLV — dùng cho nghiệp vụ đặt lịch 1-1 real-time."""

    __tablename__ = "trainer_slots"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False, index=True)
    note = Column(String(255), nullable=True)

    trainer = relationship("Trainer", back_populates="slots")
    pt_booking = relationship("PTBooking", back_populates="slot", uselist=False)


class PTBooking(Base):
    """Lịch tập 1-1 giữa hội viên và HLV."""

    __tablename__ = "pt_bookings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False, index=True)
    slot_id = Column(Integer, ForeignKey("trainer_slots.id"), unique=True, nullable=False)

    status = Column(String(50), default="confirmed")  # confirmed | completed | cancelled | no_show
    goal_note = Column(Text, nullable=True)
    trainer_feedback = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="pt_bookings")
    trainer = relationship("Trainer", back_populates="pt_bookings")
    slot = relationship("TrainerSlot", back_populates="pt_booking")


class CoachNote(Base):
    """Ghi chú / đánh giá của HLV về học viên sau buổi tập."""

    __tablename__ = "coach_notes"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    note_date = Column(Date, default=date.today, index=True)
    performance = Column(String(50), default="good")  # excellent | good | needs_work
    content = Column(Text, nullable=False)
    next_focus = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class EquipmentMaintenance(Base):
    """Phiếu bảo trì / sự cố thiết bị trong phòng tập."""

    __tablename__ = "equipment_maintenance"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False, index=True)
    issue = Column(Text, nullable=False)
    severity = Column(String(50), default="medium")  # low | medium | high
    status = Column(String(50), default="pending", index=True)  # pending | in_progress | resolved
    reported_by = Column(String(150), default="Staff")
    technician = Column(String(150), nullable=True)
    cost = Column(Float, default=0)
    reported_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    facility = relationship("Facility")