"""AI SMART FITNESS COACH — Bộ điều phối trung tâm (4 bước).

Quy trình nghiệp vụ đúng chuẩn:
    Bước 1: Thu thập dữ liệu đầu vào  (collect_input / validate_profile)
    Bước 2: Phân tích & Chẩn đoán     (ai_diagnosis.run_full_diagnosis)
    Bước 3: Thiết kế lịch tập         (ai_workout.build_workout_plan)
    Bước 4: Dinh dưỡng & Phục hồi     (ai_nutrition.build_nutrition_plan)

Đầu ra là JSON có cấu trúc (Structured Output) đúng theo JSON Schema nghiệp vụ
để frontend tự động vẽ biểu đồ, thẻ chỉ số và bảng lịch tập.

Module này cũng chứa:
    - Chuỗi câu hỏi hội thoại (Conversational Flow) cho chatbot
    - System Instruction của AI Personal Trainer & Nutritionist
    - Bộ máy trả lời dự phòng (rule-based) khi không cấu hình LLM API
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.ai_diagnosis import (
    ACTIVITY_LABELS,
    ACTIVITY_MULTIPLIERS,
    BODY_FAT_LABELS_VI,
    GOAL_LABELS,
    estimate_body_fat_us_navy,
    run_full_diagnosis,
)
from app.services.ai_workout import build_workout_plan
from app.services.ai_nutrition import build_nutrition_plan


# ==========================================================================
# SYSTEM INSTRUCTION — Personal Trainer & Nutritionist
# ==========================================================================
SYSTEM_INSTRUCTION = """# SYSTEM INSTRUCTION: AI PERSONAL TRAINER & NUTRITIONIST

## 1. VAI TRÒ CỦA BẠN
Bạn là **AI Smart Coach** — Huấn luyện viên Thể hình Cá nhân & Chuyên gia Dinh dưỡng Y học
Thể thao ảo độc quyền của hệ thống phòng Gym. Phong cách giao tiếp: Chuyên nghiệp, nhiệt
huyết, truyền động lực, khoa học, dễ hiểu và luôn đặt sự an toàn sức khỏe của hội viên lên
hàng đầu. Xưng "tôi" và gọi người dùng là "bạn".

## 2. QUY TRÌNH TƯ VẤN BẮT BUỘC (CONVERSATIONAL FLOW)
Không bao giờ đưa ra lịch tập hay thực đơn chung chung khi chưa có đủ chỉ số.

### Giai đoạn 1: Thu thập thông số cơ thể
1. **Giới tính** và **Độ tuổi**.
2. **Chiều cao (cm)** và **Cân nặng hiện tại (kg)**.
3. **Tỷ lệ mỡ cơ thể - Body Fat (%)**. Nếu chưa biết, hướng dẫn ước lượng qua ngoại hình
   hoặc đo vòng eo & vòng cổ để tính theo US Navy Method.
4. **Mục tiêu chính**: Cutting / Bulking / Body Recomposition / Sức bền.
5. **Quỹ thời gian & Tiền sử chấn thương**: số buổi/tuần, đau khớp gối, thoát vị đĩa đệm,
   đau vai, dị ứng thực phẩm.

### Giai đoạn 2: Chẩn đoán Thể trạng Khoa học
Ngay khi có đủ Cân nặng, Chiều cao và Body Fat %, PHẢI tính và trình bày:
- **BMI** = Cân nặng / (Chiều cao mét)^2
- **LBM** = Cân nặng x (1 - BodyFat% / 100)
- **Fat Mass** = Cân nặng - LBM
- **BMR (Katch-McArdle)** = 370 + (21.6 x LBM)
- **TDEE** = BMR x hệ số vận động (1.2 - 1.725)
- **Nhận định chuyên môn**: đánh giá thẳng thắn nhưng tích cực, dự báo thời gian đạt
  mục tiêu an toàn (0.5-1% trọng lượng cơ thể/tuần).

### Giai đoạn 3: Xuất Phác Đồ Toàn Diện (3 Trụ Cột)
A. **Lịch Tập Luyện Trong Tuần** — dạng bảng: Thứ/Buổi | Bài tập | Nhóm cơ | Sets x Reps |
   Thời gian nghỉ | Lưu ý kỹ thuật. Bổ sung lịch Cardio (HIIT/LISS) phù hợp Body Fat.
B. **Chế Độ Dinh Dưỡng & Thực Đơn** — Calo mục tiêu/ngày, Protein-Carb-Fat bằng gram và
   kcal, thực đơn mẫu 4 bữa với thực phẩm thuần Việt kèm định lượng gram, lượng nước/ngày.
C. **Chế Độ Nghỉ Ngơi & Phục Hồi** — số giờ ngủ, giờ đi ngủ tối ưu cho GH và MPS, hoạt
   động ngày nghỉ, NEAT 7.000-10.000 bước, cảnh báo dấu hiệu Overtraining.

## 3. NGUYÊN TẮC AN TOÀN (BẮT BUỘC TUÂN THỦ)
- BMI >= 30: khuyên tầm soát sức khỏe trước, ưu tiên bài ít tác động khớp 4-6 tuần đầu.
- Đau lưng dưới: loại bỏ Deadlift/Good Morning nặng, thay bằng RDL nhẹ, Hip Thrust, Plank.
- Đau khớp gối: hạn chế Squat sâu và nhảy, thay bằng Leg Press, Goblet Squat.
- Đau khớp vai: tránh Overhead Press và Bench biên độ lớn, thay bằng Landmine Press.
- Dị ứng thực phẩm: TUYỆT ĐỐI không đưa thực phẩm gây dị ứng vào thực đơn.
- Dưới 18 tuổi: chỉ tập tạ nhẹ - trung bình dưới giám sát, không thâm hụt calo sâu.
- Không khuyến nghị calo dưới 1200 kcal/ngày.
- Luôn nhắc: đây là tư vấn tham khảo, cần tham khảo bác sĩ nếu có bệnh lý nền.

## 4. ĐỊNH DẠNG ĐẦU RA
Trả về phần trình bày bằng tiếng Việt dễ đọc kèm bảng biểu Markdown. Song song đó, hệ thống
sẽ đính kèm khối JSON có cấu trúc theo schema nghiệp vụ để giao diện render biểu đồ,
thẻ chỉ số và bảng lịch tập. Không được bịa số liệu ngoài dữ liệu người dùng cung cấp.
"""


# ==========================================================================
# CONVERSATIONAL FLOW — Chuỗi câu hỏi onboarding
# ==========================================================================
ONBOARDING_STEPS: list[dict] = [
    {
        "step": 1,
        "field": "gender",
        "question": "Chào bạn! Tôi là AI Smart Coach của HealthyGym. Để xây dựng phác đồ "
                    "chính xác cho riêng bạn, tôi cần vài thông số cơ bản. "
                    "Đầu tiên: **giới tính** của bạn là Nam hay Nữ?",
        "hint": "Chỉ số Body Fat chuẩn được đánh giá khác nhau giữa nam và nữ.",
        "input_type": "choice",
        "options": [
            {"value": "male", "label": "Nam"},
            {"value": "female", "label": "Nữ"},
        ],
    },
    {
        "step": 2,
        "field": "age",
        "question": "Bạn **bao nhiêu tuổi**?",
        "hint": "Tuổi ảnh hưởng tới ngưỡng phân loại Body Fat và khuyến nghị cường độ tập.",
        "input_type": "number",
        "min": 10,
        "max": 90,
    },
    {
        "step": 3,
        "field": "height_cm",
        "question": "**Chiều cao** của bạn là bao nhiêu cm?",
        "hint": "Ví dụ: 172",
        "input_type": "number",
        "min": 120,
        "max": 230,
    },
    {
        "step": 4,
        "field": "weight_kg",
        "question": "**Cân nặng hiện tại** của bạn là bao nhiêu kg?",
        "hint": "Nên cân vào buổi sáng, lúc bụng đói, sau khi đi vệ sinh để có số chính xác nhất.",
        "input_type": "number",
        "min": 30,
        "max": 250,
    },
    {
        "step": 5,
        "field": "body_fat_percentage",
        "question": "Bạn có biết **tỷ lệ mỡ cơ thể (Body Fat %)** của mình không?\n\n"
                    "• Nếu đã đo máy InBody: nhập số chính xác.\n"
                    "• Nếu chưa biết: chọn \"Ước tính giúp tôi\" — tôi sẽ tính theo "
                    "công thức US Navy từ số đo vòng eo và vòng cổ của bạn.",
        "hint": "Đây là chỉ số quan trọng nhất để chọn đúng chiến lược. "
                "Ước lượng: nam 10-14% = rất nét, 15-19% = cân đối, 20-24% = có mỡ thừa, "
                ">=25% = thừa mỡ rõ. Nữ cộng thêm khoảng 8-10%.",
        "input_type": "hybrid",
        "min": 3,
        "max": 65,
        "options": [{"value": "estimate", "label": "Ước tính giúp tôi (đo vòng eo & cổ)"}],
    },
    {
        "step": 6,
        "field": "goal",
        "question": "**Mục tiêu chính** của bạn là gì?",
        "hint": "Chọn mục tiêu quan trọng nhất trong 3 tháng tới.",
        "input_type": "choice",
        "options": [
            {"value": "cutting", "label": "Giảm mỡ - Siết cơ (Cutting)"},
            {"value": "bulking", "label": "Tăng cơ - Tăng cân (Bulking)"},
            {"value": "recomp", "label": "Tăng cơ giảm mỡ đồng thời (Recomposition)"},
            {"value": "endurance", "label": "Cải thiện sức bền & thể lực"},
        ],
    },
    {
        "step": 7,
        "field": "activity_level",
        "question": "**Mức độ vận động hiện tại** của bạn thuộc nhóm nào?",
        "hint": "Chọn đúng nhất với thực tế, đừng chọn cao hơn để tránh tính sai TDEE.",
        "input_type": "choice",
        "options": [
            {"value": "sedentary", "label": "Ít vận động (chỉ làm việc văn phòng, không tập)"},
            {"value": "light", "label": "Tập nhẹ 1-3 buổi/tuần"},
            {"value": "moderate", "label": "Tập vừa 3-5 buổi/tuần"},
            {"value": "very_active", "label": "Tập nặng 6-7 buổi/tuần"},
        ],
    },
    {
        "step": 8,
        "field": "training_days_per_week",
        "question": "Bạn có thể **đi tập bao nhiêu buổi mỗi tuần**?",
        "hint": "3 buổi = Full Body | 4 buổi = Upper/Lower | 5-6 buổi = Push/Pull/Legs",
        "input_type": "number",
        "min": 2,
        "max": 6,
    },
    {
        "step": 9,
        "field": "session_minutes",
        "question": "Mỗi buổi tập bạn dành được **bao nhiêu phút**?",
        "hint": "45-60 phút là khoảng tối ưu cho hầu hết mọi người.",
        "input_type": "number",
        "min": 20,
        "max": 150,
    },
    {
        "step": 10,
        "field": "training_location",
        "question": "Bạn sẽ **tập ở đâu**?",
        "hint": "Điều này quyết định danh sách bài tập phù hợp với thiết bị bạn có.",
        "input_type": "choice",
        "options": [
            {"value": "gym", "label": "Tại phòng Gym (đầy đủ máy móc)"},
            {"value": "home_dumbbell", "label": "Tại nhà với tạ đơn"},
            {"value": "calisthenics", "label": "Calisthenics (tập với trọng lượng cơ thể)"},
        ],
    },
    {
        "step": 11,
        "field": "injuries",
        "question": "Bạn có **chấn thương hay vấn đề sức khỏe** nào cần lưu ý không?\n\n"
                    "Chọn tất cả những vùng đang đau hoặc đã từng chấn thương. "
                    "Nếu không có, chọn \"Không có\".",
        "hint": "Tôi sẽ tự động loại bỏ bài tập nguy hiểm và thay bằng bài an toàn tương đương.",
        "input_type": "multi",
        "options": [
            {"value": "lower_back", "label": "Đau lưng dưới / Thoát vị đĩa đệm"},
            {"value": "knee", "label": "Đau khớp gối"},
            {"value": "shoulder", "label": "Đau khớp vai"},
            {"value": "wrist", "label": "Đau cổ tay"},
            {"value": "hip", "label": "Đau khớp hông"},
            {"value": "none", "label": "Không có"},
        ],
    },
    {
        "step": 12,
        "field": "allergies",
        "question": "Bạn có **dị ứng thực phẩm** nào không?\n\n"
                    "Tôi sẽ thay thế các món gây dị ứng trong thực đơn bằng món tương đương "
                    "về dinh dưỡng.",
        "hint": "Chọn tất cả những gì bạn dị ứng. Nếu không có, chọn \"Không có\".",
        "input_type": "multi",
        "options": [
            {"value": "fish", "label": "Cá"},
            {"value": "seafood", "label": "Hải sản (tôm, cua, mực)"},
            {"value": "egg", "label": "Trứng"},
            {"value": "dairy", "label": "Sữa & sản phẩm từ sữa"},
            {"value": "lactose", "label": "Không dung nạp lactose"},
            {"value": "peanut", "label": "Đậu phộng"},
            {"value": "nut", "label": "Các loại hạt"},
            {"value": "gluten", "label": "Gluten (lúa mì)"},
            {"value": "none", "label": "Không có"},
        ],
    },
]

#: Các trường bắt buộc để chạy chẩn đoán (Trụ cột 2)
REQUIRED_FIELDS = [
    "gender", "age", "height_cm", "weight_kg",
    "body_fat_percentage", "goal", "activity_level",
]

#: Các trường cá nhân hoá thêm (Trụ cột 3 & 4). Có giá trị mặc định nên KHÔNG
#: chặn việc chạy chẩn đoán — chỉ hỏi khi người dùng muốn phác đồ chi tiết hơn.
OPTIONAL_FIELDS = [
    "training_days_per_week", "session_minutes",
    "training_location", "injuries", "allergies",
]

#: Giá trị mặc định hợp lý cho các trường tuỳ chọn
FIELD_DEFAULTS: dict[str, object] = {
    "training_days_per_week": 4,
    "session_minutes": 60,
    "training_location": "gym",
    "injuries": [],
    "allergies": [],
}


def get_onboarding_flow() -> dict:
    """Trả về toàn bộ chuỗi câu hỏi onboarding cho frontend render wizard."""
    return {
        "total_steps": len(ONBOARDING_STEPS),
        "required_fields": REQUIRED_FIELDS,
        "steps": ONBOARDING_STEPS,
    }


def next_missing_field(profile: dict, include_optional: bool = False) -> Optional[dict]:
    """Xác định câu hỏi kế tiếp còn thiếu — cốt lõi của Conversational Flow.

    Mặc định chỉ hỏi các chỉ số BẮT BUỘC (đủ để chạy chẩn đoán Trụ cột 2).
    Đặt include_optional=True để hỏi tiếp nhóm câu hỏi cá nhân hoá lịch tập,
    dinh dưỡng, chấn thương và dị ứng.
    """
    steps = ONBOARDING_STEPS if include_optional else [
        s for s in ONBOARDING_STEPS if s["field"] in REQUIRED_FIELDS
    ]
    for step in steps:
        field_name = step["field"]
        value = profile.get(field_name)
        if field_name in ("injuries", "allergies"):
            continue  # không bắt buộc
        if value is None or value == "":
            return step
    return None


def validate_profile(profile: dict) -> list[str]:
    """Kiểm tra tính hợp lệ của dữ liệu đầu vào. Trả về danh sách lỗi."""
    errors: list[str] = []

    if profile.get("gender") not in ("male", "female"):
        errors.append("Giới tính phải là 'male' hoặc 'female'.")

    age = profile.get("age")
    if age is None:
        errors.append("Thiếu độ tuổi.")
    elif not (10 <= float(age) <= 90):
        errors.append("Độ tuổi phải trong khoảng 10 - 90.")

    height = profile.get("height_cm")
    if height is None:
        errors.append("Thiếu chiều cao.")
    elif not (120 <= float(height) <= 230):
        errors.append("Chiều cao phải trong khoảng 120 - 230 cm.")

    weight = profile.get("weight_kg")
    if weight is None:
        errors.append("Thiếu cân nặng.")
    elif not (30 <= float(weight) <= 250):
        errors.append("Cân nặng phải trong khoảng 30 - 250 kg.")

    bf = profile.get("body_fat_percentage")
    if bf is None:
        errors.append("Thiếu tỷ lệ mỡ cơ thể (Body Fat %).")
    elif not (3 <= float(bf) <= 65):
        errors.append("Body Fat % phải trong khoảng 3 - 65.")

    if profile.get("goal") not in GOAL_LABELS:
        errors.append("Mục tiêu không hợp lệ (cutting/bulking/recomp/endurance).")

    if profile.get("activity_level") not in ACTIVITY_MULTIPLIERS:
        errors.append("Mức độ vận động không hợp lệ.")

    return errors


def apply_defaults(profile: dict) -> dict:
    """Điền giá trị mặc định cho các trường tuỳ chọn còn thiếu."""
    merged = dict(profile)
    for key, default in FIELD_DEFAULTS.items():
        if merged.get(key) in (None, "", []):
            merged[key] = list(default) if isinstance(default, list) else default
    return merged


def parse_csv_list(raw: Any) -> list[str]:
    """Chuẩn hoá trường CSV (chấn thương / dị ứng) thành list, loại bỏ 'none'."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        items = [str(x).strip().lower() for x in raw]
    else:
        items = [x.strip().lower() for x in str(raw).split(",")]
    return [x for x in items if x and x != "none"]


# ==========================================================================
# BƯỚC 2 -> 4: SINH PHÁC ĐỒ HOÀN CHỈNH
# ==========================================================================
def generate_full_plan(
    *,
    height_cm: float,
    weight_kg: float,
    body_fat_percentage: float,
    gender: str = "male",
    age: Optional[int] = None,
    activity_level: str = "moderate",
    goal: str = "cutting",
    training_days_per_week: int = 4,
    session_minutes: int = 60,
    training_location: str = "gym",
    injuries: Optional[list[str]] = None,
    allergies: Optional[list[str]] = None,
) -> dict:
    """Chạy đủ 3 trụ cột và trả về JSON có cấu trúc theo schema nghiệp vụ."""
    injuries = parse_csv_list(injuries)
    allergies = parse_csv_list(allergies)

    # --- BƯỚC 2: Chẩn đoán thể trạng ---
    diagnosis = run_full_diagnosis(
        height_cm=height_cm,
        weight_kg=weight_kg,
        body_fat_percentage=body_fat_percentage,
        gender=gender,
        age=age,
        activity_level=activity_level,
        goal=goal,
        injuries=injuries,
        training_hours_per_week=max(1, int(training_days_per_week * session_minutes / 60)),
    )

    # --- BƯỚC 3: Lịch tập luyện ---
    workout = build_workout_plan(
        goal=goal,
        activity_level=activity_level,
        training_days_per_week=training_days_per_week,
        session_minutes=session_minutes,
        training_location=training_location,
        body_fat_pct=body_fat_percentage,
        gender=gender,
        injuries=injuries,
        age=age,
    )

    # --- BƯỚC 4: Dinh dưỡng & Phục hồi ---
    nutrition = build_nutrition_plan(
        diagnosis=diagnosis,
        goal=goal,
        training_days_per_week=training_days_per_week,
        session_minutes=session_minutes,
        allergies=allergies,
        age=age,
        injuries=injuries,
    )

    recovery = nutrition.pop("recovery_plan")

    member_diagnosis = {
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "body_fat_percentage": body_fat_percentage,
        "age": age,
        "gender": gender,
        "bmi": diagnosis.bmi,
        "bmi_category": diagnosis.bmi_category,
        "lean_body_mass_kg": diagnosis.lean_body_mass_kg,
        "fat_mass_kg": diagnosis.fat_mass_kg,
        "bmr_kcal": int(round(diagnosis.bmr_kcal)),
        "tdee_kcal": int(round(diagnosis.tdee_kcal)),
        "activity_multiplier": diagnosis.activity_multiplier,
        "activity_label": ACTIVITY_LABELS.get(activity_level, ""),
        "body_fat_category": diagnosis.body_fat_category,
        "body_fat_category_vi": diagnosis.body_fat_category_vi,
        "ffmi": diagnosis.ffmi,
        "ffmi_normalized": diagnosis.ffmi_normalized,
        "ffmi_interpretation": diagnosis.ffmi_interpretation,
        "muscle_quality": diagnosis.muscle_quality,
        "body_type": diagnosis.body_type,
        "body_type_classification": diagnosis.body_type_vi,
        "ai_assessment_summary": diagnosis.ai_assessment_summary,
        "estimated_weeks_to_goal": diagnosis.estimated_weeks_to_goal,
        "estimated_months_to_goal": round(diagnosis.estimated_weeks_to_goal / 4.3, 1),
        "target_body_fat_percentage": diagnosis.target_body_fat_percentage,
        "fat_to_lose_kg": diagnosis.fat_to_lose_kg,
        "muscle_to_gain_kg": diagnosis.muscle_to_gain_kg,
        "weekly_fat_loss_target_kg": diagnosis.weekly_fat_loss_kg,
        "safety_warnings": diagnosis.warnings,
    }

    plan = {
        "goal": goal,
        "goal_label": GOAL_LABELS.get(goal, ""),
        "member_diagnosis": member_diagnosis,
        "nutrition_plan": nutrition,
        "workout_schedule": workout,
        "recovery_protocol": recovery,
        "disclaimer": (
            "Phác đồ này được tạo tự động bởi AI Smart Coach dựa trên thông số bạn cung cấp, "
            "theo các nguyên tắc dinh dưỡng và huấn luyện thể thao phổ quát. "
            "Đây là tư vấn tham khảo, không thay thế chẩn đoán y khoa. "
            "Nếu bạn có bệnh lý nền (tim mạch, tiểu đường, huyết áp, tuyến giáp) hoặc đang "
            "mang thai, hãy tham khảo ý kiến bác sĩ trước khi bắt đầu."
        ),
        "safety_warnings": member_diagnosis["safety_warnings"],
    }
    plan["summary_text"] = build_summary_text(plan)
    return plan


def build_summary_text(plan: dict) -> str:
    """Sinh đoạn tóm tắt tiếng Việt để hiển thị nổi bật trên giao diện."""
    d = plan["member_diagnosis"]
    n = plan["nutrition_plan"]
    w = plan["workout_schedule"]
    m = n["macros"]

    lines = [
        f"**Chẩn đoán:** {d['body_type_classification']} — BMI {d['bmi']}, "
        f"Body Fat {d['body_fat_percentage']}% ({d['body_fat_category']}), "
        f"cơ nạc {d['lean_body_mass_kg']}kg, mỡ {d['fat_mass_kg']}kg.",

        f"**Năng lượng:** BMR {d['bmr_kcal']} kcal → TDEE {d['tdee_kcal']} kcal → "
        f"mục tiêu **{n['target_daily_calories']} kcal/ngày** "
        f"({'+' if n['caloric_adjustment'] >= 0 else ''}{n['caloric_adjustment']} kcal).",

        f"**Macros:** Protein {m['protein_grams']}g • Carb {m['carbs_grams']}g • "
        f"Fat {m['fat_grams']}g — nước {n['daily_water_liters']} lít/ngày.",

        f"**Lịch tập:** {w['split_type']} — mỗi buổi ~{w['session_minutes']} phút.",

        f"**Lộ trình:** khoảng {d['estimated_weeks_to_goal']} tuần "
        f"(~{d['estimated_months_to_goal']} tháng).",
    ]
    return "\n".join(lines)


# ==========================================================================
# FALLBACK RULE-BASED CHAT (khi chưa cấu hình LLM API)
# ==========================================================================
def rule_based_reply(message: str, profile: Optional[dict] = None, context: Optional[dict] = None) -> dict:
    """Trả lời dự phòng theo luật khi không có LLM.

    Vẫn tuân thủ đúng Conversational Flow: hỏi đủ chỉ số trước khi xuất phác đồ.
    """
    from app.services.ai_diagnosis import estimate_body_fat_us_navy as _navy

    text = (message or "").strip().lower()
    profile = dict(profile or {})

    # --- A. Hội viên cung cấp số đo vòng để ước tính Body Fat ---
    if context and context.get("estimate_body_fat"):
        try:
            bf = _navy(
                gender=context.get("gender", "male"),
                height_cm=float(context["height_cm"]),
                neck_cm=float(context["neck_cm"]),
                waist_cm=float(context["waist_cm"]),
                hip_cm=float(context["hip_cm"]) if context.get("hip_cm") else None,
            )
            return {
                "reply": (
                    f"Tôi đã tính xong theo công thức US Navy Method!\n\n"
                    f"**Tỷ lệ mỡ cơ thể ước tính của bạn: {bf}%**\n\n"
                    f"Đây là phương pháp ước lượng dựa trên số đo thước dây, sai số thường "
                    f"trong khoảng ±3-4% so với đo máy InBody. Nếu có dịp, bạn nên đo InBody "
                    f"tại phòng Gym để có con số chính xác nhất.\n\n"
                    f"Tôi sẽ dùng chỉ số này để chạy chẩn đoán thể trạng cho bạn."
                ),
                "action": "body_fat_estimated",
                "body_fat_percentage": bf,
            }
        except (ValueError, KeyError, TypeError) as exc:
            return {
                "reply": f"Tôi chưa tính được Body Fat: {exc}. "
                         f"Bạn kiểm tra lại số đo giúp tôi nhé (đơn vị cm).",
                "action": "need_body_fat",
            }

    # --- B. Câu hỏi về giá gói tập / khuyến mãi ---
    if any(k in text for k in ("giá", "gói tập", "bao nhiêu tiền", "voucher", "khuyến mãi", "phí")):
        return {
            "reply": (
                "Bảng giá gói hội viên HealthyGym:\n\n"
                "| Gói | Thời hạn | Giá | Đặc quyền |\n"
                "|---|---|---|---|\n"
                "| Linh hoạt | 1 tháng | 399.000đ | 1 chi nhánh, tập 24/7, lớp nhóm miễn phí |\n"
                "| Toàn hệ thống | 6 tháng | 1.799.000đ | Mọi chi nhánh, đo InBody, 2 buổi PT |\n"
                "| Tự động | 1 tháng | 349.000đ | Tự động gia hạn, tập 24/7 |\n"
                "| Super VIP | 12 tháng | 3.290.000đ | 15+ chi nhánh, 6 buổi PT 1-1 |\n\n"
                "Mã giảm giá đang hiệu lực: **GIAM10** (giảm 10%) và **HEALTHY20** "
                "(giảm 20%, tối đa 500k). Bạn muốn tôi tư vấn gói nào phù hợp với mục tiêu "
                "của bạn không?"
            ),
            "action": "pricing_info",
        }

    # --- C. Câu hỏi về lịch lớp học ---
    if any(k in text for k in ("lịch lớp", "lớp học", "yoga", "hiit", "boxing", "zumba", "group x")):
        return {
            "reply": (
                "Lịch lớp tập nhóm tại HealthyGym:\n\n"
                "• **Hatha Yoga** — Thứ 2, 4, 6 (07:00-08:00), Studio Group X\n"
                "• **HIIT Đốt Mỡ Toàn Thân** — Thứ 3, 5, 7 (18:30-19:30), Khu Functional\n"
                "• **Zumba & Dance Fitness** — Thứ 2, 4, 6 (19:00-20:00), Studio Lầu 2\n"
                "• **Kỹ Thuật Tập Tạ Cơ Bản** — Thứ 3, 5, 7 (17:30-18:30), Khu Free Weight\n\n"
                "Bạn cần có thẻ hội viên còn hạn để đặt chỗ. Vào mục **Lịch Lớp Tập** để "
                "xem số chỗ trống và đặt ngay."
            ),
            "action": "classes_info",
        }

    # --- D. Câu hỏi về bảo lưu thẻ ---
    if any(k in text for k in ("bảo lưu", "tạm dừng", "freeze", "đóng băng")):
        return {
            "reply": (
                "Chính sách bảo lưu thẻ:\n\n"
                "• Hội viên có thẻ đang hoạt động được bảo lưu từ **1 đến 60 ngày**.\n"
                "• Số ngày bảo lưu sẽ được **cộng bù tự động** vào hạn thẻ của bạn.\n"
                "• Trong thời gian bảo lưu, bạn không thể check-in hoặc đặt lịch lớp.\n\n"
                "Vào mục **Thẻ Của Tôi** → nhập số ngày → bấm *Bảo lưu thẻ*. "
                "Khi muốn tập lại, bấm *Mở khóa thẻ* và hệ thống sẽ tự tính lại hạn thẻ."
            ),
            "action": "freeze_policy",
        }

    # --- E. Đã đủ dữ liệu -> chạy chẩn đoán ---
    if not validate_profile(profile) and context and context.get("run_diagnosis"):
        plan = generate_full_plan(
            height_cm=float(profile["height_cm"]),
            weight_kg=float(profile["weight_kg"]),
            body_fat_percentage=float(profile["body_fat_percentage"]),
            gender=profile["gender"],
            age=int(profile["age"]),
            activity_level=profile.get("activity_level", "moderate"),
            goal=profile.get("goal", "cutting"),
            training_days_per_week=int(profile.get("training_days_per_week", 4)),
            session_minutes=int(profile.get("session_minutes", 60)),
            training_location=profile.get("training_location", "gym"),
            injuries=profile.get("injuries"),
            allergies=profile.get("allergies"),
        )
        return {
            "reply": "Tôi đã chạy xong chẩn đoán thể trạng và lập phác đồ 3 trụ cột cho bạn. "
                     "Xem chi tiết ở khung phác đồ bên cạnh nhé!",
            "action": "plan_generated",
            "plan": plan,
        }

    # --- F. Còn thiếu chỉ số -> hỏi tiếp theo đúng thứ tự ---
    missing = next_missing_field(profile)
    if missing:
        filled = [f for f in REQUIRED_FIELDS if profile.get(f) not in (None, "")]
        progress = f"({len(filled)}/{len(REQUIRED_FIELDS)} chỉ số đã thu thập)"
        return {
            "reply": f"{missing['question']}\n\n_{missing.get('hint', '')}_\n\n{progress}",
            "action": "collect_input",
            "next_step": missing,
            "collected_fields": filled,
        }

    # --- G. Đủ chỉ số nhưng chưa yêu cầu chạy -> mời chạy ---
    if not validate_profile(profile):
        return {
            "reply": (
                "Tôi đã có đủ thông số của bạn rồi! Bấm nút **Xuất phác đồ AI** để tôi "
                "chạy chẩn đoán thể trạng và lập kế hoạch tập luyện - dinh dưỡng - phục hồi "
                "chi tiết cho bạn nhé."
            ),
            "action": "ready_to_generate",
        }

    # --- H. Chào hỏi / mặc định ---
    return {
        "reply": (
            "Chào bạn! Tôi là **AI Smart Coach** — Huấn luyện viên thể hình và chuyên gia "
            "dinh dưỡng ảo của HealthyGym.\n\n"
            "Tôi có thể giúp bạn:\n"
            "• **Chẩn đoán thể trạng** và lập phác đồ tập luyện + dinh dưỡng cá nhân hoá\n"
            "• Tính **BMI, Body Fat, BMR, TDEE** và nhu cầu calo mỗi ngày\n"
            "• Thiết kế **lịch tập theo số buổi/tuần** (Full Body / Upper-Lower / Push-Pull-Legs)\n"
            "• Lên **thực đơn Việt Nam** với định lượng gram cụ thể\n"
            "• Tư vấn gói tập, lịch lớp học và chính sách bảo lưu thẻ\n\n"
            "Để bắt đầu, hãy cho tôi biết **giới tính và độ tuổi** của bạn, hoặc bấm nút "
            "**Bắt đầu chẩn đoán** để điền form từng bước."
        ),
        "action": "greeting",
    }