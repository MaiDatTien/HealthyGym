"""Schemas cho phân hệ AI Smart Fitness Coach, tiến độ và PT 1-1."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


# ==========================================================================
# AI COACH
# ==========================================================================
class DiagnosisRequest(BaseModel):
    """Chẩn đoán nhanh — dùng cho công cụ tính trên trang chủ (không cần đăng nhập)."""

    height_cm: float = Field(..., gt=100, lt=250, description="Chiều cao (cm)")
    weight_kg: float = Field(..., gt=20, lt=300, description="Cân nặng (kg)")
    body_fat_percentage: Optional[float] = Field(
        None, gt=2, lt=70, description="Tỷ lệ mỡ cơ thể (%). Bỏ trống nếu dùng số đo vòng."
    )
    gender: str = Field("male", description="male hoặc female")
    age: Optional[int] = Field(None, ge=10, le=90)
    activity_level: str = Field("moderate", description="sedentary|light|moderate|very_active")
    goal: str = Field("cutting", description="cutting|bulking|recomp|endurance")

    # Nếu chưa biết Body Fat %, gửi số đo để hệ thống tự ước tính (US Navy Method)
    neck_cm: Optional[float] = Field(None, gt=10, lt=80)
    waist_cm: Optional[float] = Field(None, gt=30, lt=200)
    hip_cm: Optional[float] = Field(None, gt=30, lt=200)


class BodyFatEstimateRequest(BaseModel):
    """Ước tính Body Fat % theo US Navy Method từ số đo thước dây."""

    gender: str = "male"
    height_cm: float = Field(..., gt=100, lt=250)
    neck_cm: float = Field(..., gt=10, lt=80, description="Vòng cổ (cm)")
    waist_cm: float = Field(..., gt=30, lt=200, description="Vòng eo tại rốn (cm)")
    hip_cm: Optional[float] = Field(
        None, gt=30, lt=200, description="Vòng hông (cm) — bắt buộc với nữ"
    )


class AIPlanRequest(BaseModel):
    """Yêu cầu xuất phác đồ AI đầy đủ 3 trụ cột."""

    height_cm: float = Field(..., gt=100, lt=250)
    weight_kg: float = Field(..., gt=20, lt=300)
    body_fat_percentage: float = Field(..., gt=2, lt=70)
    gender: str = "male"
    age: Optional[int] = Field(None, ge=10, le=90)
    activity_level: str = "moderate"
    goal: str = "cutting"
    training_days_per_week: int = Field(4, ge=2, le=6)
    session_minutes: int = Field(60, ge=20, le=150)
    training_location: str = Field("gym", description="gym|home_dumbbell|calisthenics")
    injuries: Optional[List[str]] = Field(
        default=None, description="VD: ['lower_back','knee']"
    )
    allergies: Optional[List[str]] = Field(
        default=None, description="VD: ['fish','dairy']"
    )

    # Số đo thước dây (tuỳ chọn) — lưu kèm hồ sơ để theo dõi vòng eo qua các tuần
    waist_cm: Optional[float] = Field(None, gt=30, lt=200, description="Vòng eo (cm)")
    neck_cm: Optional[float] = Field(None, gt=10, lt=80, description="Vòng cổ (cm)")
    hip_cm: Optional[float] = Field(None, gt=30, lt=200, description="Vòng hông (cm)")

    save_to_profile: bool = Field(
        True, description="Lưu vào hồ sơ sức khỏe của hội viên (cần đăng nhập)"
    )


class AIChatRequest(BaseModel):
    """Hội thoại với AI Smart Coach theo Conversational Flow."""

    message: str = Field(..., min_length=1, max_length=2000)
    profile: Optional[dict] = Field(
        default=None,
        description="Các chỉ số đã thu thập qua các lượt trước đó",
    )
    estimate_body_fat: bool = Field(
        False, description="True khi tin nhắn chứa số đo vòng để ước tính Body Fat"
    )
    run_diagnosis: bool = Field(
        False, description="True khi hội viên yêu cầu xuất phác đồ"
    )
    session_key: Optional[str] = None


# ==========================================================================
# TIẾN ĐỘ & NHẬT KÝ
# ==========================================================================
class HealthMetricCreate(BaseModel):
    measured_at: Optional[date] = None
    height_cm: float = Field(..., gt=100, lt=250)
    weight_kg: float = Field(..., gt=20, lt=300)
    body_fat_percentage: Optional[float] = Field(None, gt=2, lt=70)
    age: Optional[int] = Field(None, ge=10, le=90)
    gender: Optional[str] = "male"

    muscle_mass_kg: Optional[float] = Field(None, ge=0, lt=150)
    visceral_fat_level: Optional[float] = Field(None, ge=0, lt=40)
    waist_cm: Optional[float] = Field(None, gt=30, lt=200)
    neck_cm: Optional[float] = Field(None, gt=10, lt=80)
    hip_cm: Optional[float] = Field(None, gt=30, lt=200)
    body_water_kg: Optional[float] = Field(None, ge=0, lt=100)

    source: str = Field("manual", description="inbody|manual|ai_coach|staff")
    note: Optional[str] = None


class WorkoutLogCreate(BaseModel):
    log_date: Optional[date] = None
    session_focus: Optional[str] = None
    exercise_name: str = Field(..., min_length=2, max_length=200)
    target_muscle: Optional[str] = None
    sets: Optional[int] = Field(None, ge=1, le=20)
    reps: Optional[int] = Field(None, ge=1, le=200)
    weight_kg: Optional[float] = Field(None, ge=0, le=600)
    rpe: Optional[float] = Field(None, ge=1, le=10)
    duration_minutes: Optional[int] = Field(None, ge=1, le=400)
    calories_burned: Optional[float] = Field(None, ge=0, le=5000)
    notes: Optional[str] = None


class DailyCheckinCreate(BaseModel):
    log_date: Optional[date] = None
    calories_in: Optional[float] = Field(None, ge=0, le=12000)
    protein_g: Optional[float] = Field(None, ge=0, le=600)
    carbs_g: Optional[float] = Field(None, ge=0, le=1500)
    fat_g: Optional[float] = Field(None, ge=0, le=600)
    water_liters: Optional[float] = Field(None, ge=0, le=15)
    sleep_hours: Optional[float] = Field(None, ge=0, le=16)
    steps: Optional[int] = Field(None, ge=0, le=100000)
    weight_kg: Optional[float] = Field(None, ge=20, le=300)
    mood: Optional[str] = None
    note: Optional[str] = None


# ==========================================================================
# PT 1-1 & CHECK-IN QR
# ==========================================================================
class TrainerSlotCreate(BaseModel):
    trainer_id: int
    branch_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    note: Optional[str] = None


class PTBookingCreate(BaseModel):
    slot_id: int
    goal_note: Optional[str] = None


class CoachNoteCreate(BaseModel):
    member_id: int
    performance: str = Field("good", description="excellent|good|needs_work")
    content: str = Field(..., min_length=5)
    next_focus: Optional[str] = None


class PTFeedbackInput(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None


class QRCheckinRequest(BaseModel):
    qr_code: str = Field(..., min_length=4, description="Mã QR trên thẻ hội viên")
    branch_id: Optional[int] = None


# ==========================================================================
# THIẾT BỊ & BẢO TRÌ
# ==========================================================================
class MaintenanceCreate(BaseModel):
    facility_id: int
    issue: str = Field(..., min_length=5)
    severity: str = Field("medium", description="low|medium|high")
    technician: Optional[str] = None
    cost: float = Field(0, ge=0)


class MaintenanceResolve(BaseModel):
    status: str = Field("resolved", description="pending|in_progress|resolved")
    technician: Optional[str] = None
    cost: Optional[float] = Field(None, ge=0)