"""Models cho phân hệ AI Smart Fitness Coach & Theo dõi tiến độ.

Bao gồm:
- HealthMetric   : chỉ số cơ thể theo từng lần đo (InBody / AI ước tính / nhập tay)
- AIPlan         : phác đồ 3 trụ cột do AI Coach sinh ra (đã lưu cấu trúc JSON)
- WorkoutLog     : nhật ký tập luyện (Progressive Overload)
- DailyCheckin   : nhật ký dinh dưỡng / nước / giấc ngủ / bước chân
- InBodyRecord   : phiếu InBody chuyên sâu (SMM, BFM, mỡ nội tạng, phân tích vùng)
- PARQScreening  : sàng lọc an toàn y tế bắt buộc trước khi lên lịch tập
- WeeklyCheckin  : đánh giá định kỳ Chủ Nhật + nhật ký hiệu chỉnh động
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    ForeignKey, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base
from app.models.interaction import now_local


class HealthMetric(Base):
    """Một lần đo chỉ số cơ thể của hội viên."""

    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    measured_at = Column(Date, default=date.today, index=True)

    # --- Chỉ số bắt buộc ---
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    body_fat_percentage = Column(Float, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(10), default="male")  # male | female

    # --- Chỉ số mở rộng (InBody / thước dây) ---
    muscle_mass_kg = Column(Float, nullable=True)
    visceral_fat_level = Column(Float, nullable=True)
    waist_cm = Column(Float, nullable=True)
    neck_cm = Column(Float, nullable=True)
    hip_cm = Column(Float, nullable=True)
    body_water_kg = Column(Float, nullable=True)

    # --- Kết quả engine tính toán (lưu lại để vẽ biểu đồ, không cần tính lại) ---
    bmi = Column(Float, nullable=True)
    lean_body_mass_kg = Column(Float, nullable=True)
    fat_mass_kg = Column(Float, nullable=True)
    bmr_kcal = Column(Float, nullable=True)
    tdee_kcal = Column(Float, nullable=True)
    body_type_classification = Column(String(150), nullable=True)

    source = Column(String(50), default="ai_coach")  # ai_coach | inbody | manual | staff
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="health_metrics")


class AIPlan(Base):
    """Phác đồ AI hoàn chỉnh: Chẩn đoán + Dinh dưỡng + Lịch tập + Phục hồi."""

    __tablename__ = "ai_plans"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    metric_id = Column(Integer, ForeignKey("health_metrics.id"), nullable=True)

    # --- Input người dùng ---
    goal = Column(String(50), default="cutting")  # cutting | bulking | recomp | endurance
    activity_level = Column(String(50), default="moderate")
    training_days_per_week = Column(Integer, default=4)
    session_minutes = Column(Integer, default=60)
    training_location = Column(String(50), default="gym")  # gym | home_dumbbell | calisthenics
    injuries = Column(Text, nullable=True)      # CSV: lower_back,knee,shoulder
    allergies = Column(Text, nullable=True)     # CSV thực phẩm dị ứng

    # --- Kết quả then chốt (cột phẳng để query/thống kê) ---
    split_type = Column(String(150), nullable=True)
    target_daily_calories = Column(Float, nullable=True)
    caloric_adjustment = Column(Float, nullable=True)
    protein_grams = Column(Float, nullable=True)
    carbs_grams = Column(Float, nullable=True)
    fat_grams = Column(Float, nullable=True)
    daily_water_liters = Column(Float, nullable=True)
    estimated_weeks_to_goal = Column(Integer, nullable=True)

    # --- Toàn bộ phác đồ dạng JSON để render giao diện ---
    diagnosis_json = Column(Text, nullable=True)
    nutrition_json = Column(Text, nullable=True)
    workout_json = Column(Text, nullable=True)
    recovery_json = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="ai_plans")


class WorkoutLog(Base):
    """Nhật ký từng hiệp tập — dữ liệu cho Progressive Overload."""

    __tablename__ = "workout_logs"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    ai_plan_id = Column(Integer, ForeignKey("ai_plans.id"), nullable=True)
    log_date = Column(Date, default=date.today, index=True)

    session_focus = Column(String(200), nullable=True)   # VD: Upper Body A
    exercise_name = Column(String(200), nullable=False)
    target_muscle = Column(String(200), nullable=True)
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    rpe = Column(Float, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    calories_burned = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyCheckin(Base):
    """Nhật ký hằng ngày: calo nạp, đạm, nước, giấc ngủ, số bước chân."""

    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    log_date = Column(Date, default=date.today, index=True)

    calories_in = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    water_liters = Column(Float, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    steps = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    mood = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local)


# ==========================================================================
# SÀNG LỌC AN TOÀN Y TẾ (PAR-Q+) — BẮT BUỘC TRƯỚC KHI LÊN LỊCH TẬP
# ==========================================================================
class PARQScreening(Base):
    """Bảng sàng lọc PAR-Q+ (Physical Activity Readiness Questionnaire).

    Kết quả sàng lọc quyết định các "hard rules" mà AI Workout Planner phải tuân thủ:
    cấm bài nén trục cột sống, cấm cardio chấn động, v.v.
    """

    __tablename__ = "parq_screenings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    screened_at = Column(Date, default=date.today, index=True)

    # --- Câu hỏi PAR-Q chuẩn (7 câu) ---
    q_heart_condition = Column(Boolean, default=False)      # bệnh tim mạch
    q_chest_pain = Column(Boolean, default=False)           # đau ngực khi vận động
    q_dizziness = Column(Boolean, default=False)            # chóng mặt / mất thăng bằng
    q_chronic_disease = Column(Boolean, default=False)      # huyết áp, tiểu đường, hen
    q_bone_joint = Column(Boolean, default=False)           # vấn đề xương khớp
    q_medication = Column(Boolean, default=False)           # đang dùng thuốc điều trị
    q_other_reason = Column(Boolean, default=False)         # lý do khác

    # --- Chi tiết bệnh lý / chấn thương cụ thể ---
    has_heart_disease = Column(Boolean, default=False)
    has_hypertension = Column(Boolean, default=False)
    has_diabetes = Column(Boolean, default=False)
    has_asthma = Column(Boolean, default=False)
    has_herniated_disc = Column(Boolean, default=False)     # thoát vị đĩa đệm
    disc_levels = Column(String(50), nullable=True)         # VD: "L4-L5, S1"
    has_cervical_degeneration = Column(Boolean, default=False)  # thoái hóa đốt sống cổ
    has_acl_tear = Column(Boolean, default=False)           # đứt/rách dây chằng chéo
    has_rotator_cuff = Column(Boolean, default=False)       # đau khớp vai
    is_pregnant = Column(Boolean, default=False)
    postpartum_months = Column(Integer, nullable=True)      # số tháng sau sinh
    other_conditions = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)

    # --- Kết luận ---
    needs_medical_clearance = Column(Boolean, default=False, index=True)
    risk_level = Column(String(20), default="low", index=True)  # low|moderate|high
    clearance_required_note = Column(Text, nullable=True)

    # --- Hard rules sinh ra (JSON list các mã cấm) ---
    contraindications_json = Column(Text, nullable=True)
    safe_exercise_notes_json = Column(Text, nullable=True)

    screened_by = Column(String(150), default="self")
    created_at = Column(DateTime, default=now_local)

    member = relationship("Member")


# ==========================================================================
# PHIẾU INBODY CHUYÊN SÂU
# ==========================================================================
class InBodyRecord(Base):
    """Phiếu đo InBody chuyên sâu: SMM, BFM, mỡ nội tạng và phân tích từng vùng.

    Phân tích vùng giúp phát hiện mất cân bằng cơ bắp (VD: tay trái yếu hơn tay phải,
    chân yếu hơn thân trên) để AI bổ sung bài tập đơn bên (unilateral).
    """

    __tablename__ = "inbody_records"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    metric_id = Column(Integer, ForeignKey("health_metrics.id"), nullable=True)
    measured_at = Column(Date, default=date.today, index=True)

    # --- Chỉ số tổng thể ---
    skeletal_muscle_mass_kg = Column(Float, nullable=True)   # SMM
    body_fat_mass_kg = Column(Float, nullable=True)          # BFM
    body_fat_percentage = Column(Float, nullable=True)
    visceral_fat_level = Column(Float, nullable=True)        # chuẩn < 10
    body_water_kg = Column(Float, nullable=True)
    protein_kg = Column(Float, nullable=True)
    mineral_kg = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    basal_metabolic_rate = Column(Float, nullable=True)
    waist_hip_ratio = Column(Float, nullable=True)

    # --- Phân tích cơ theo vùng (kg) ---
    lean_left_arm = Column(Float, nullable=True)
    lean_right_arm = Column(Float, nullable=True)
    lean_trunk = Column(Float, nullable=True)
    lean_left_leg = Column(Float, nullable=True)
    lean_right_leg = Column(Float, nullable=True)

    # --- Phân tích mỡ theo vùng (kg) ---
    fat_left_arm = Column(Float, nullable=True)
    fat_right_arm = Column(Float, nullable=True)
    fat_trunk = Column(Float, nullable=True)
    fat_left_leg = Column(Float, nullable=True)
    fat_right_leg = Column(Float, nullable=True)

    # --- Kết luận engine ---
    shape_type = Column(String(5), nullable=True)            # C | I | D
    shape_description = Column(String(255), nullable=True)
    balance_score = Column(Float, nullable=True)             # 0-100, càng cao càng cân đối
    imbalances_json = Column(Text, nullable=True)            # danh sách mất cân bằng
    recommendations_json = Column(Text, nullable=True)

    # Mốc so sánh với lần đo trước
    delta_muscle_kg = Column(Float, nullable=True)
    delta_fat_kg = Column(Float, nullable=True)

    image_url = Column(String(500), nullable=True)
    device_model = Column(String(100), default="InBody 570")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_local)

    member = relationship("Member")


# ==========================================================================
# ĐÁNH GIÁ ĐỊNH KỲ & HIỆU CHỈNH ĐỘNG
# ==========================================================================
class WeeklyCheckin(Base):
    """Check-in Chủ Nhật hằng tuần + nhật ký hiệu chỉnh động của AI.

    Dữ liệu đầu vào để phát hiện chững cân (plateau) và mất cơ (quá tải).
    """

    __tablename__ = "weekly_checkins"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    ai_plan_id = Column(Integer, ForeignKey("ai_plans.id"), nullable=True)
    week_start = Column(Date, nullable=False, index=True)

    # --- Số liệu hội viên báo cáo ---
    avg_weight_kg = Column(Float, nullable=True)       # cân nặng trung bình tuần
    waist_cm = Column(Float, nullable=True)
    sessions_completed = Column(Integer, default=0)    # số buổi tập thực tế
    sessions_planned = Column(Integer, default=0)
    hunger_level = Column(Integer, nullable=True)      # 1-5
    sleep_quality = Column(Integer, nullable=True)     # 1-5
    energy_level = Column(Integer, nullable=True)      # 1-5
    stress_level = Column(Integer, nullable=True)      # 1-5
    adherence_percent = Column(Float, nullable=True)   # % tuân thủ dinh dưỡng
    note = Column(Text, nullable=True)

    # --- Kết quả phân tích của AI ---
    weight_change_kg = Column(Float, nullable=True)
    weight_change_percent = Column(Float, nullable=True)
    detected_issue = Column(String(40), nullable=True)  # plateau|muscle_loss|overtraining|on_track
    adjustment_type = Column(String(40), nullable=True) # calorie_cut|calorie_increase|cardio_add|refeed|deload|none
    adjustment_detail = Column(Text, nullable=True)
    calorie_delta = Column(Float, default=0)            # thay đổi calo đề xuất
    ai_feedback = Column(Text, nullable=True)

    created_at = Column(DateTime, default=now_local)

    member = relationship("Member")

    __table_args__ = (
        UniqueConstraint("member_id", "week_start", name="uq_weekly_checkin"),
    )


class ChecklistItem(Base):
    """Mục việc cần làm của hội viên (nhắc nhở từ AI/HLV/lễ tân)."""

    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    detail = Column(Text, nullable=True)
    source = Column(String(30), default="ai")     # ai | trainer | receptionist | system
    due_date = Column(Date, nullable=True)
    is_done = Column(Boolean, default=False, index=True)
    done_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_local)