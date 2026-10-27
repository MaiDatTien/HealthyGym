"""Models cho GAMIFICATION, CRM GIỮ CHÂN HỘI VIÊN & THIẾT BỊ.

Bao gồm:
    MemberStreak        : chuỗi ngày/tuần đi tập không đứt quãng
    Badge / MemberBadge : huy hiệu thành tích
    Challenge / ChallengeEntry : thử thách biến đổi hình thể 90 ngày
    LoyaltyPoint        : sổ cái điểm thưởng
    Reward / RewardRedemption : quà đổi điểm
    Referral            : giới thiệu bạn bè
    RetentionTask       : task chăm sóc hội viên có nguy cơ rời bỏ
    ChurnRiskSnapshot   : ảnh chụp rủi ro rời bỏ theo ngày
    RenewalReminder     : nhắc gia hạn theo các mốc 30/14/7/3 ngày
    MachineQR           : mã QR trên từng máy tập + hướng dẫn sử dụng
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    ForeignKey, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base
from app.models.interaction import now_local


class PointKind:
    CHECKIN = "checkin"
    WORKOUT_GOAL = "workout_goal"
    REFERRAL = "referral"
    CHALLENGE = "challenge"
    PURCHASE = "purchase"
    REDEEM = "redeem"
    BONUS = "bonus"
    ALL = (CHECKIN, WORKOUT_GOAL, REFERRAL, CHALLENGE, PURCHASE, REDEEM, BONUS)


# --------------------------------------------------------------------------
# STREAK & HUY HIỆU
# --------------------------------------------------------------------------
class MemberStreak(Base):
    """Chuỗi đi tập liên tục — nguồn dữ liệu cho gamification."""

    __tablename__ = "member_streaks"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), unique=True, nullable=False)

    current_week_streak = Column(Integer, default=0)   # số tuần liên tiếp đạt mục tiêu
    longest_week_streak = Column(Integer, default=0)
    current_day_streak = Column(Integer, default=0)
    longest_day_streak = Column(Integer, default=0)

    last_activity_date = Column(Date, nullable=True, index=True)
    total_checkins = Column(Integer, default=0)
    total_workouts_logged = Column(Integer, default=0)
    this_week_visits = Column(Integer, default=0)

    updated_at = Column(DateTime, default=now_local, onupdate=now_local)

    member = relationship("Member")


class Badge(Base):
    """Định nghĩa huy hiệu thành tích."""

    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(30), default="strength", index=True)  # strength|cardio|consistency|social
    #: Điều kiện tự động: loại + ngưỡng (VD: bench_press_1rm >= 100)
    criteria_type = Column(String(40), nullable=True)   # checkin_count|streak|1rm|points|challenge
    criteria_value = Column(Float, default=0)
    criteria_exercise = Column(String(150), nullable=True)
    point_reward = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)


class MemberBadge(Base):
    """Huy hiệu hội viên đã đạt được."""

    __tablename__ = "member_badges"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime, default=now_local, index=True)
    progress_value = Column(Float, default=0)
    note = Column(Text, nullable=True)

    member = relationship("Member")
    badge = relationship("Badge")

    __table_args__ = (
        UniqueConstraint("member_id", "badge_id", name="uq_badge_per_member"),
    )


# --------------------------------------------------------------------------
# THỬ THÁCH BIẾN ĐỔI HÌNH THỂ
# --------------------------------------------------------------------------
class Challenge(Base):
    """Thử thách (VD: 90-Day Transformation Challenge)."""

    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    kind = Column(String(30), default="transformation")  # transformation|consistency|strength
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    max_participants = Column(Integer, default=200)
    entry_fee = Column(Float, default=0)
    prize_description = Column(Text, nullable=True)
    reward_points = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=now_local)

    entries = relationship("ChallengeEntry", back_populates="challenge", cascade="all, delete-orphan")


class ChallengeEntry(Base):
    """Hội viên tham gia thử thách, kèm ảnh Before/After và chỉ số đầu-cuối kỳ."""

    __tablename__ = "challenge_entries"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)

    # --- Chỉ số đầu kỳ ---
    start_weight_kg = Column(Float, nullable=True)
    start_body_fat = Column(Float, nullable=True)
    start_muscle_kg = Column(Float, nullable=True)
    before_photo_url = Column(String(500), nullable=True)

    # --- Chỉ số cuối kỳ ---
    end_weight_kg = Column(Float, nullable=True)
    end_body_fat = Column(Float, nullable=True)
    end_muscle_kg = Column(Float, nullable=True)
    after_photo_url = Column(String(500), nullable=True)

    # --- Điểm & xếp hạng ---
    score = Column(Float, default=0)
    rank = Column(Integer, nullable=True)
    votes = Column(Integer, default=0)
    status = Column(String(20), default="active", index=True)  # active|completed|disqualified
    joined_at = Column(DateTime, default=now_local)

    challenge = relationship("Challenge", back_populates="entries")
    member = relationship("Member")

    __table_args__ = (
        UniqueConstraint("challenge_id", "member_id", name="uq_entry_per_challenge"),
    )


# --------------------------------------------------------------------------
# ĐIỂM THƯỞNG & ĐỔI QUÀ
# --------------------------------------------------------------------------
class LoyaltyPoint(Base):
    """Sổ cái điểm thưởng."""

    __tablename__ = "loyalty_points"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    points = Column(Integer, nullable=False)         # dương = cộng, âm = trừ
    balance_after = Column(Integer, nullable=False)
    kind = Column(String(30), default=PointKind.CHECKIN, index=True)
    reference = Column(String(80), nullable=True)
    note = Column(Text, nullable=True)
    expires_at = Column(Date, nullable=True)
    created_at = Column(DateTime, default=now_local, index=True)

    member = relationship("Member")


class Reward(Base):
    """Quà đổi bằng điểm."""

    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    points_cost = Column(Integer, nullable=False)
    kind = Column(String(30), default="voucher")   # voucher|pt_session|product|service
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    value_amount = Column(Float, default=0)        # giá trị quy đổi (VND)
    stock = Column(Integer, default=0)             # 0 = không giới hạn
    is_active = Column(Boolean, default=True, index=True)


class RewardRedemption(Base):
    """Lịch sử đổi quà."""

    __tablename__ = "reward_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    points_spent = Column(Integer, nullable=False)
    status = Column(String(20), default="pending", index=True)  # pending|fulfilled|cancelled
    fulfilled_by = Column(String(150), nullable=True)
    code = Column(String(40), nullable=True)        # mã voucher sinh ra
    created_at = Column(DateTime, default=now_local)
    fulfilled_at = Column(DateTime, nullable=True)

    member = relationship("Member")
    reward = relationship("Reward")


class Referral(Base):
    """Giới thiệu bạn bè — cộng điểm khi người được giới thiệu chốt gói."""

    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    referred_name = Column(String(255), nullable=False)
    referred_phone = Column(String(30), nullable=False, index=True)
    referred_member_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    referral_code = Column(String(40), unique=True, index=True, nullable=False)

    status = Column(String(20), default="pending", index=True)  # pending|converted|expired
    points_awarded = Column(Integer, default=0)
    created_at = Column(DateTime, default=now_local)
    converted_at = Column(DateTime, nullable=True)

    referrer = relationship("Member", foreign_keys=[referrer_member_id])


# --------------------------------------------------------------------------
# CRM GIỮ CHÂN HỘI VIÊN
# --------------------------------------------------------------------------
class RetentionTask(Base):
    """Task chăm sóc hội viên có nguy cơ rời bỏ, giao cho Sale/CSKH."""

    __tablename__ = "retention_tasks"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    kind = Column(String(30), default="sleeping_7d", index=True)  # sleeping_7d|sleeping_14d|sleeping_30d|renewal
    priority = Column(String(20), default="medium", index=True)   # low|medium|high
    title = Column(String(255), nullable=False)
    detail = Column(Text, nullable=True)
    suggested_action = Column(Text, nullable=True)
    assigned_to = Column(String(150), nullable=True, index=True)
    status = Column(String(20), default="open", index=True)       # open|in_progress|done|dismissed
    outcome = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=now_local, index=True)
    resolved_at = Column(DateTime, nullable=True)

    member = relationship("Member")


class ChurnRiskSnapshot(Base):
    """Ảnh chụp rủi ro rời bỏ — phục vụ báo cáo Churn Rate."""

    __tablename__ = "churn_risk_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    snapshot_date = Column(Date, default=date.today, index=True)
    days_since_last_visit = Column(Integer, default=0)
    visits_last_30d = Column(Integer, default=0)
    risk_score = Column(Float, default=0)          # 0-100, càng cao càng nguy cơ
    risk_level = Column(String(20), default="low", index=True)  # low|medium|high|critical
    factors_json = Column(Text, nullable=True)

    member = relationship("Member")

    __table_args__ = (
        UniqueConstraint("member_id", "snapshot_date", name="uq_churn_snapshot_per_day"),
    )


class RenewalReminder(Base):
    """Nhắc gia hạn tự động tại các mốc 30/14/7/3 ngày trước khi hết hạn."""

    __tablename__ = "renewal_reminders"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("membership_contracts.id"), nullable=False)
    days_before_expiry = Column(Integer, nullable=False)   # 30|14|7|3
    channel = Column(String(20), default="in_app")        # in_app|email|sms|zalo
    offer_text = Column(Text, nullable=True)              # ưu đãi Early Bird
    discount_percent = Column(Integer, default=0)
    status = Column(String(20), default="pending", index=True)  # pending|sent|converted|expired
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_local)

    member = relationship("Member")

    __table_args__ = (
        UniqueConstraint("contract_id", "days_before_expiry",
                         name="uq_reminder_per_contract_milestone"),
    )


# --------------------------------------------------------------------------
# MÃ QR TRÊN TỪNG MÁY TẬP
# --------------------------------------------------------------------------
class MachineQR(Base):
    """Mã QR dán trên thân máy — quét để xem hướng dẫn sử dụng và báo hỏng."""

    __tablename__ = "machine_qrs"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False, index=True)
    qr_code = Column(String(60), unique=True, index=True, nullable=False)
    machine_code = Column(String(40), nullable=False)   # VD: "TREADMILL-07"
    display_name = Column(String(255), nullable=False)

    # --- Hướng dẫn sử dụng ---
    video_url = Column(String(500), nullable=True)
    setup_guide = Column(Text, nullable=True)          # cách chỉnh ghế, tầm tay
    posture_guide = Column(Text, nullable=True)        # tư thế chuẩn
    common_mistakes = Column(Text, nullable=True)      # lỗi sai thường gặp
    target_muscles = Column(String(255), nullable=True)
    difficulty = Column(String(20), default="beginner")

    # --- Liên kết với thư viện bài tập AI ---
    exercise_name = Column(String(200), nullable=True)

    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=now_local)

    facility = relationship("Facility")