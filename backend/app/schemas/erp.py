"""Schemas cho toàn bộ 7 phân hệ nghiệp vụ ERP."""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import date, datetime


# ==========================================================================
# VÒNG ĐỜI HỢP ĐỒNG HỘI VIÊN
# ==========================================================================
class ContractCreate(BaseModel):
    member_id: int
    plan_id: int
    branch_id: Optional[int] = None
    tier: Literal["standard", "gold", "vip"] = "standard"
    time_window: Literal["off_peak", "full_time"] = "full_time"
    start_date: Optional[date] = None
    voucher_code: Optional[str] = None
    payment_method: str = "Chuyển khoản QR"
    sold_by: Optional[str] = None
    #: Trả góp: số kỳ (0 = thanh toán một lần)
    installment_count: int = Field(0, ge=0, le=24)
    down_payment: float = Field(0, ge=0)
    note: Optional[str] = None


class FreezeCreate(BaseModel):
    days: int = Field(..., ge=1, le=60, description="Số ngày bảo lưu")
    reason: Optional[str] = None
    start_date: Optional[date] = None


class FreezeApproval(BaseModel):
    approved: bool = True
    note: Optional[str] = None


class TransferCreate(BaseModel):
    to_full_name: str = Field(..., min_length=2)
    to_phone: str = Field(..., min_length=8)
    to_email: Optional[str] = None
    reason: Optional[str] = None


class UpgradeCreate(BaseModel):
    new_plan_id: int
    payment_method: str = "Chuyển khoản QR"


class InstallmentPay(BaseModel):
    amount: float = Field(..., gt=0)
    method: str = "cash"
    note: Optional[str] = None


class LeadCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=8)
    email: Optional[str] = None
    source: str = "website"
    branch_id: Optional[int] = None
    interested_plan_id: Optional[int] = None


class LeadUpdate(BaseModel):
    stage: Optional[str] = None
    assigned_to: Optional[str] = None
    consultation_note: Optional[str] = None
    lost_reason: Optional[str] = None
    interested_plan_id: Optional[int] = None


class TrialPassRequest(BaseModel):
    full_name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=8)
    days: int = Field(7, ge=1, le=14)
    branch_id: Optional[int] = None


class OTPVerify(BaseModel):
    phone: str
    otp_code: str = Field(..., min_length=4, max_length=10)


class WalletTopup(BaseModel):
    amount: float = Field(..., gt=0, le=50000000)
    method: str = "cash"
    note: Optional[str] = None


# ==========================================================================
# PT & GÓI BUỔI TẬP
# ==========================================================================
class PTPackageCreate(BaseModel):
    name: str
    sessions: int = Field(..., ge=1, le=500)
    price: float = Field(..., ge=0)
    validity_days: int = Field(180, ge=7, le=1095)
    tier: str = "standard"
    includes_inbody: bool = True
    includes_nutrition: bool = False
    description: Optional[str] = None


class PTPackagePurchaseCreate(BaseModel):
    member_id: int
    package_id: int
    trainer_id: Optional[int] = None
    payment_method: str = "Chuyển khoản QR"
    sold_by: Optional[str] = None


class BurnSessionRequest(BaseModel):
    """PT bấm hoàn thành buổi tập (bước 1 của xác nhận kép)."""

    booking_id: int
    note: Optional[str] = None


class BurnConfirmRequest(BaseModel):
    """Hội viên xác nhận cuối buổi (bước 2 của xác nhận kép)."""

    booking_id: int
    method: Literal["qr", "otp", "app_button"] = "app_button"
    otp_code: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback: Optional[str] = None


class TrainerShiftCreate(BaseModel):
    trainer_id: int
    weekday: int = Field(..., ge=0, le=6, description="0=Thứ 2 ... 6=Chủ Nhật")
    start_hour: int = Field(..., ge=0, le=23)
    end_hour: int = Field(..., ge=1, le=24)
    branch_id: Optional[int] = None


class TrainerChangeCreate(BaseModel):
    requested_trainer_id: Optional[int] = None
    booking_id: Optional[int] = None
    kind: Literal["change", "substitution"] = "change"
    reason: Optional[str] = None


class PayrollGenerate(BaseModel):
    year: int = Field(..., ge=2020, le=2100)
    month: int = Field(..., ge=1, le=12)
    trainer_id: Optional[int] = None


# ==========================================================================
# GROUP-X
# ==========================================================================
class ClassScheduleCreate(BaseModel):
    gym_class_id: int
    trainer_id: Optional[int] = None
    branch_id: Optional[int] = None
    studio: str = "Studio A"
    start_time: datetime
    end_time: datetime
    capacity: int = Field(25, ge=1, le=200)
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    requires_spot_selection: bool = False
    spot_layout: Literal["mat", "bike", "none"] = "none"
    note: Optional[str] = None


class ClassBookRequest(BaseModel):
    schedule_id: int
    spot_id: Optional[int] = None
    note: Optional[str] = None


class SubstituteTrainerAssign(BaseModel):
    substitute_trainer_id: int
    note: Optional[str] = None


# ==========================================================================
# CHECK-IN CỔNG & TỦ ĐỒ
# ==========================================================================
class GateScanRequest(BaseModel):
    """Quét mã QR động tại cổng."""

    qr_token: str = Field(..., min_length=4)
    branch_id: Optional[int] = None
    direction: Literal["in", "out"] = "in"


class LockerAssignRequest(BaseModel):
    member_id: int
    zone: Optional[Literal["male", "female", "vip"]] = None
    towels: int = Field(1, ge=0, le=5)
    locker_id: Optional[int] = None


class LockerReturn(BaseModel):
    towels_returned: int = Field(1, ge=0, le=5)
    key_returned: bool = True
    penalty_amount: float = Field(0, ge=0)
    penalty_reason: Optional[str] = None


class LockerRentalCreate(BaseModel):
    member_id: int
    months: int = Field(1, ge=1, le=12)
    zone: Literal["male", "female", "vip"] = "vip"


# ==========================================================================
# POS & KHO
# ==========================================================================
class ProductCreate(BaseModel):
    sku: str = Field(..., min_length=2)
    name: str
    category: Literal["drink", "supplement", "accessory", "service"] = "supplement"
    brand: Optional[str] = None
    unit: str = "hũ"
    servings_per_unit: int = Field(0, ge=0)
    price: float = Field(..., ge=0)
    serving_price: float = Field(0, ge=0)
    cost_price: float = Field(0, ge=0)
    stock_quantity: float = Field(0, ge=0)
    low_stock_threshold: float = Field(5, ge=0)
    expiry_date: Optional[date] = None
    description: Optional[str] = None


class InventoryImport(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0)
    unit_cost: float = Field(0, ge=0)
    note: Optional[str] = None


class PosOrderItemInput(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0)
    #: True nếu bán lẻ theo muỗng thay vì nguyên hũ
    by_serving: bool = False


class PosCheckout(BaseModel):
    items: List[PosOrderItemInput] = Field(..., min_length=1)
    member_id: Optional[int] = None
    customer_name: Optional[str] = None
    payment_method: Literal["cash", "transfer", "wallet", "card"] = "cash"
    discount_amount: float = Field(0, ge=0)
    branch_id: Optional[int] = None
    note: Optional[str] = None


# ==========================================================================
# GAMIFICATION & CRM
# ==========================================================================
class LeaderboardQuery(BaseModel):
    period: Literal["week", "month", "all"] = "month"
    metric: Literal["checkins", "points", "streak", "volume"] = "checkins"
    limit: int = Field(20, ge=1, le=100)


class ChallengeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    kind: Literal["transformation", "consistency", "strength"] = "transformation"
    start_date: date
    end_date: date
    max_participants: int = Field(200, ge=1)
    entry_fee: float = Field(0, ge=0)
    prize_description: Optional[str] = None
    reward_points: int = Field(1000, ge=0)


class ChallengeJoin(BaseModel):
    challenge_id: int
    start_weight_kg: Optional[float] = None
    start_body_fat: Optional[float] = None
    start_muscle_kg: Optional[float] = None
    before_photo_url: Optional[str] = None


class ChallengeFinalize(BaseModel):
    end_weight_kg: Optional[float] = None
    end_body_fat: Optional[float] = None
    end_muscle_kg: Optional[float] = None
    after_photo_url: Optional[str] = None


class RewardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    points_cost: int = Field(..., ge=1)
    kind: Literal["voucher", "pt_session", "product", "service"] = "voucher"
    product_id: Optional[int] = None
    value_amount: float = Field(0, ge=0)
    stock: int = Field(0, ge=0)


class RewardRedeem(BaseModel):
    reward_id: int


class ReferralCreate(BaseModel):
    referred_name: str = Field(..., min_length=2)
    referred_phone: str = Field(..., min_length=8)


class RetentionTaskUpdate(BaseModel):
    status: Optional[Literal["open", "in_progress", "done", "dismissed"]] = None
    assigned_to: Optional[str] = None
    outcome: Optional[str] = None


class RenewalOfferCreate(BaseModel):
    contract_id: int
    days_before_expiry: Literal[30, 14, 7, 3] = 30
    discount_percent: int = Field(0, ge=0, le=50)
    offer_text: Optional[str] = None
    channel: Literal["in_app", "email", "sms", "zalo"] = "in_app"


# ==========================================================================
# THIẾT BỊ & MÃ QR MÁY
# ==========================================================================
class MachineQRCreate(BaseModel):
    facility_id: int
    machine_code: str
    display_name: str
    video_url: Optional[str] = None
    setup_guide: Optional[str] = None
    posture_guide: Optional[str] = None
    common_mistakes: Optional[str] = None
    target_muscles: Optional[str] = None
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    exercise_name: Optional[str] = None


class EquipmentReport(BaseModel):
    """Hội viên/PT báo hỏng thiết bị từ trang quét QR."""

    facility_id: int
    issue: str = Field(..., min_length=5)
    severity: Literal["low", "medium", "high"] = "medium"
    machine_qr_code: Optional[str] = None


class MaintenanceSchedule(BaseModel):
    facility_id: int
    maintenance_cycle_days: int = Field(90, ge=7, le=730)
    next_maintenance_date: Optional[date] = None
    note: Optional[str] = None


# ==========================================================================
# AI NÂNG CAO: SÀNG LỌC, INBODY, ĐỔI BÀI, ĐỔI MÓN, CHECK-IN TUẦN
# ==========================================================================
class PARQSubmit(BaseModel):
    member_id: Optional[int] = None

    q_heart_condition: bool = False
    q_chest_pain: bool = False
    q_dizziness: bool = False
    q_chronic_disease: bool = False
    q_bone_joint: bool = False
    q_medication: bool = False
    q_other_reason: bool = False

    has_heart_disease: bool = False
    has_hypertension: bool = False
    has_diabetes: bool = False
    has_asthma: bool = False
    has_herniated_disc: bool = False
    disc_levels: Optional[str] = None
    has_cervical_degeneration: bool = False
    has_acl_tear: bool = False
    has_rotator_cuff: bool = False
    is_pregnant: bool = False
    postpartum_months: Optional[int] = Field(None, ge=0, le=60)
    other_conditions: Optional[str] = None
    current_medications: Optional[str] = None


class InBodySubmit(BaseModel):
    member_id: Optional[int] = None
    measured_at: Optional[date] = None

    height_cm: Optional[float] = Field(None, gt=100, lt=250)
    weight_kg: Optional[float] = Field(None, gt=20, lt=300)
    body_fat_percentage: Optional[float] = Field(None, gt=2, lt=70)
    gender: str = "male"
    age: Optional[int] = Field(None, ge=10, le=90)

    skeletal_muscle_mass_kg: Optional[float] = Field(None, ge=0, lt=120)
    body_fat_mass_kg: Optional[float] = Field(None, ge=0, lt=150)
    visceral_fat_level: Optional[float] = Field(None, ge=0, lt=40)
    body_water_kg: Optional[float] = Field(None, ge=0, lt=100)
    protein_kg: Optional[float] = Field(None, ge=0, lt=50)
    mineral_kg: Optional[float] = Field(None, ge=0, lt=20)
    waist_cm: Optional[float] = Field(None, gt=30, lt=200)
    hip_cm: Optional[float] = Field(None, gt=30, lt=200)
    basal_metabolic_rate: Optional[float] = Field(None, ge=500, le=6000)

    lean_left_arm: Optional[float] = Field(None, ge=0, lt=20)
    lean_right_arm: Optional[float] = Field(None, ge=0, lt=20)
    lean_trunk: Optional[float] = Field(None, ge=0, lt=60)
    lean_left_leg: Optional[float] = Field(None, ge=0, lt=30)
    lean_right_leg: Optional[float] = Field(None, ge=0, lt=30)

    fat_left_arm: Optional[float] = Field(None, ge=0, lt=20)
    fat_right_arm: Optional[float] = Field(None, ge=0, lt=20)
    fat_trunk: Optional[float] = Field(None, ge=0, lt=60)
    fat_left_leg: Optional[float] = Field(None, ge=0, lt=30)
    fat_right_leg: Optional[float] = Field(None, ge=0, lt=30)

    device_model: str = "InBody 570"
    note: Optional[str] = None
    save_to_profile: bool = True


class ExerciseSwapRequest(BaseModel):
    exercise_name: str
    reason: Literal[
        "equipment_busy", "equipment_broken", "joint_pain",
        "no_equipment", "too_hard", "preference",
    ] = "preference"
    branch_id: Optional[int] = None
    max_results: int = Field(4, ge=1, le=10)


class FoodSwapRequest(BaseModel):
    food_key: str
    grams: float = Field(..., gt=0, le=2000)
    prioritize: Literal["protein", "calories", "carbs", "fat"] = "protein"
    max_results: int = Field(5, ge=1, le=10)


class CheatMealRequest(BaseModel):
    excess_calories: float = Field(..., gt=0, le=8000)
    meal_description: Optional[str] = None
    days_available: int = Field(4, ge=1, le=7)


class WeeklyCheckinSubmit(BaseModel):
    avg_weight_kg: Optional[float] = Field(None, gt=20, lt=300)
    waist_cm: Optional[float] = Field(None, gt=30, lt=200)
    sessions_completed: int = Field(0, ge=0, le=21)
    sessions_planned: int = Field(0, ge=0, le=21)
    hunger_level: Optional[int] = Field(None, ge=1, le=5)
    sleep_quality: Optional[int] = Field(None, ge=1, le=5)
    energy_level: Optional[int] = Field(None, ge=1, le=5)
    stress_level: Optional[int] = Field(None, ge=1, le=5)
    adherence_percent: Optional[float] = Field(None, ge=0, le=100)
    note: Optional[str] = None


class ProgressiveOverloadRequest(BaseModel):
    exercise_name: str
    sets: List[dict] = Field(..., min_length=1)
    target_reps_upper: int = Field(10, ge=1, le=50)


class OneRmRequest(BaseModel):
    weight_kg: float = Field(..., gt=0, le=600)
    reps: int = Field(..., ge=1, le=30)


class DeloadRequest(BaseModel):
    weeks_training: int = Field(..., ge=1, le=200)
    deload_count: int = Field(0, ge=0, le=50)
    training_days_per_week: int = Field(4, ge=2, le=6)


class CarbCyclingRequest(BaseModel):
    target_calories: float = Field(..., gt=500, le=8000)
    protein_g: float = Field(..., gt=0, le=500)
    carbs_g: float = Field(..., gt=0, le=1500)
    fat_g: float = Field(..., gt=0, le=400)
    training_days_per_week: int = Field(4, ge=2, le=6)
    goal: str = "recomp"