from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


def now_local() -> datetime:
    """Giờ địa phương dạng naive — dùng thống nhất cho dữ liệu vận hành.

    Toàn bộ nghiệp vụ phòng gym (check-in, khung giờ dạy của HLV, lịch lớp)
    được ghi và so sánh theo giờ địa phương của phòng tập. Dùng chung một mốc
    thời gian giúp tránh lệch múi giờ khiến việc so sánh "trong vòng 30 phút"
    hoặc hiển thị giờ check-in bị sai.
    """
    return datetime.now()

class Voucher(Base):
    __tablename__ = "vouchers"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    discount_percent = Column(Integer, default=10)
    max_discount_amount = Column(Float, default=500000)
    is_active = Column(Boolean, default=True)
    valid_until = Column(DateTime, nullable=True)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=False)
    voucher_code = Column(String(50), nullable=True)
    discount_amount = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="Chuyển khoản")
    status = Column(String(50), default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="orders")
    plan = relationship("MembershipPlan")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    gym_class_id = Column(Integer, ForeignKey("gym_classes.id"), nullable=False)
    booking_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="confirmed")  # confirmed, cancelled, attended
    note = Column(Text, nullable=True)

    member = relationship("Member", back_populates="bookings")
    gym_class = relationship("GymClass", back_populates="bookings")

class CheckInLog(Base):
    __tablename__ = "checkin_logs"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    checked_by = Column(String(150), default="Staff")
    checkin_time = Column(DateTime, default=now_local)

    member = relationship("Member", back_populates="checkins")

class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(Integer, primary_key=True, index=True)
    member_name = Column(String(255), nullable=False)
    rating = Column(Integer, default=5)
    comment = Column(Text, nullable=False)
    reply = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
