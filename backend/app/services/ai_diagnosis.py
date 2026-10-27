"""AI DIAGNOSIS ENGINE — Chẩn đoán thể trạng khoa học.

Toàn bộ công thức theo đúng chuẩn nghiệp vụ của Smart AI Gym Platform:
    1. BMI          = Cân nặng / (Chiều cao mét)^2
    2. LBM          = Cân nặng x (1 - BodyFat% / 100)
    3. BMR          = 370 + 21.6 x LBM              (Katch-McArdle, cần Body Fat %)
    4. TDEE         = BMR x ActivityMultiplier
    5. Xếp loại BF% theo Giới tính + Độ tuổi
    6. US Navy Method để ước tính Body Fat % từ số đo thước dây

Module này là pure-function, không phụ thuộc DB => dễ unit test và tái sử dụng
cho cả API lẫn AI Coach.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

# --------------------------------------------------------------------------
# HẰNG SỐ NGHIỆP VỤ
# --------------------------------------------------------------------------

#: Hệ số vận động (Activity Multiplier) theo mức độ hoạt động
ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,    # Ít vận động - chỉ làm việc văn phòng
    "light": 1.375,      # Tập nhẹ 1-3 buổi/tuần
    "moderate": 1.55,    # Tập vừa 3-5 buổi/tuần
    "very_active": 1.725,  # Tập nặng 6-7 buổi/tuần
    "extra_active": 1.9,   # Vận động viên / lao động nặng + tập 2 lần/ngày
}

ACTIVITY_LABELS: dict[str, str] = {
    "sedentary": "Ít vận động (chỉ làm việc văn phòng, không tập)",
    "light": "Tập nhẹ 1-3 buổi/tuần",
    "moderate": "Tập vừa 3-5 buổi/tuần",
    "very_active": "Tập nặng 6-7 buổi/tuần",
    "extra_active": "Vận động viên (tập 2 buổi/ngày)",
}

GOAL_LABELS: dict[str, str] = {
    "cutting": "Giảm mỡ - Siết cơ (Cutting)",
    "bulking": "Tăng cơ - Tăng cân (Bulking)",
    "recomp": "Tăng cơ giảm mỡ đồng thời (Body Recomposition)",
    "endurance": "Duy trì thể lực & Sức bền",
}

#: Ngưỡng phân loại Body Fat % theo giới tính (dải tuổi 20-39 làm chuẩn)
BODY_FAT_RANGES: dict[str, list[tuple[str, float, float]]] = {
    "male": [
        ("Essential", 2.0, 5.0),
        ("Athletes", 6.0, 13.0),
        ("Fitness", 14.0, 17.0),
        ("Average", 18.0, 24.0),
        ("Obese", 25.0, 100.0),
    ],
    "female": [
        ("Essential", 10.0, 13.0),
        ("Athletes", 14.0, 20.0),
        ("Fitness", 21.0, 24.0),
        ("Average", 25.0, 31.0),
        ("Obese", 32.0, 100.0),
    ],
}

BODY_FAT_LABELS_VI: dict[str, str] = {
    "Essential": "Mỡ thiết yếu (Essential) - Mức tối thiểu để cơ thể sống khỏe",
    "Athletes": "Vận động viên (Athletes) - Thể trạng thi đấu chuyên nghiệp",
    "Fitness": "Săn chắc (Fitness) - Thể trạng lý tưởng, cơ nét rõ",
    "Average": "Trung bình (Average) - Còn mỡ thừa, cần siết lại",
    "Obese": "Béo phì (Obese) - Nguy cơ sức khỏe, cần giảm mỡ ưu tiên",
}

#: Mục tiêu Body Fat % khi kết thúc lộ trình.
#: Đặt ở MÉP TRÊN của nhóm "Fitness" làm cột mốc đầu tiên — đây là ngưỡng
#: săn chắc - cơ nét nhưng vẫn đạt được trong 3-5 tháng với tốc độ an toàn,
#: thay vì nhắm thẳng vào nhóm "Athletes" (dễ dẫn tới mất cơ và tụt hormone).
TARGET_BODY_FAT: dict[str, dict[str, float]] = {
    "cutting": {"male": 17.0, "female": 24.0},
    "bulking": {"male": 18.0, "female": 26.0},
    "recomp": {"male": 15.0, "female": 23.0},
    "endurance": {"male": 15.0, "female": 24.0},
}

#: Tốc độ giảm mỡ an toàn: 0.5 - 1% trọng lượng cơ thể / tuần
SAFE_FAT_LOSS_RATE_PER_WEEK = (0.005, 0.01)
#: Tốc độ tăng cơ thực tế cho người tập tự nhiên: 0.25 - 0.5% / tuần
SAFE_MUSCLE_GAIN_RATE_PER_WEEK = (0.0025, 0.005)

#: Loại tạng người (Body Type)
BODY_TYPES: dict[str, str] = {
    "skinny_fat": "Skinny Fat - Thừa mỡ nhưng thiếu cơ",
    "obese": "Obese - Béo phì, thừa mỡ đáng kể",
    "overweight": "Overweight - Thừa cân mức trung bình",
    "athletic": "Athletic - Thể trạng vận động viên",
    "lean": "Lean - Gọn gàng, ít mỡ",
    "skinny": "Skinny - Gầy, cần tăng cơ",
    "average": "Average - Trung bình, cần cải thiện tỷ lệ cơ/mỡ",
}


# --------------------------------------------------------------------------
# DTO
# --------------------------------------------------------------------------
@dataclass
class DiagnosisResult:
    """Kết quả chẩn đoán thể trạng đầy đủ."""

    height_cm: float
    weight_kg: float
    body_fat_percentage: float
    age: Optional[int]
    gender: str

    bmi: float
    bmi_category: str
    lean_body_mass_kg: float
    fat_mass_kg: float
    bmr_kcal: float
    tdee_kcal: float
    activity_multiplier: float

    body_fat_category: str
    body_fat_category_vi: str
    ffmi: float
    ffmi_normalized: float
    ffmi_interpretation: str
    muscle_quality: str

    body_type: str
    body_type_vi: str
    ai_assessment_summary: str
    estimated_weeks_to_goal: int
    target_body_fat_percentage: float
    fat_to_lose_kg: float
    muscle_to_gain_kg: float
    weekly_fat_loss_kg: float
    warnings: list[str] = field(default_factory=list)
    water_min_liters: float = 0.0


# --------------------------------------------------------------------------
# CÔNG THỨC CƠ BẢN
# --------------------------------------------------------------------------
def calc_bmi(weight_kg: float, height_cm: float) -> float:
    """BMI = Cân nặng(kg) / Chiều cao(m)^2."""
    height_m = height_cm / 100.0
    if height_m <= 0:
        raise ValueError("Chiều cao phải lớn hơn 0")
    return round(weight_kg / (height_m ** 2), 2)


def bmi_category(bmi: float) -> str:
    """Phân loại BMI theo chuẩn WHO cho người châu Á."""
    if bmi < 18.5:
        return "Thiếu cân (Underweight)"
    if bmi < 23.0:
        return "Bình thường (Normal)"
    if bmi < 25.0:
        return "Thừa cân nhẹ (At risk)"
    if bmi < 30.0:
        return "Thừa cân / Béo phì độ I"
    return "Béo phì độ II trở lên"


def calc_lean_body_mass(weight_kg: float, body_fat_pct: float) -> float:
    """LBM = Cân nặng x (1 - BodyFat% / 100)."""
    return round(weight_kg * (1 - body_fat_pct / 100.0), 2)


def calc_bmr_katch_mcardle(lbm_kg: float) -> float:
    """BMR = 370 + (21.6 x LBM) — chính xác nhất khi đã có Body Fat %."""
    return round(370 + (21.6 * lbm_kg), 1)


def calc_tdee(bmr: float, activity_level: str) -> float:
    """TDEE = BMR x ActivityMultiplier."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    return round(bmr * multiplier, 1)


def calc_ffmi(lbm_kg: float, height_cm: float) -> tuple[float, float]:
    """Fat-Free Mass Index và bản chuẩn hóa theo chiều cao.

    FFMI = LBM(kg) / Chiều cao(m)^2
    FFMI_normalized = FFMI + 6.1 x (1.8 - Chiều cao mét)
    """
    height_m = height_cm / 100.0
    ffmi = lbm_kg / (height_m ** 2)
    normalized = ffmi + 6.1 * (1.8 - height_m)
    return round(ffmi, 2), round(normalized, 2)


def estimate_body_fat_us_navy(
    gender: str,
    height_cm: float,
    neck_cm: float,
    waist_cm: float,
    hip_cm: Optional[float] = None,
) -> float:
    """Ước tính Body Fat % theo US Navy Method (số đo tính bằng cm).

    Nam : 495 / (1.0324 - 0.19077*log10(eo - cổ) + 0.15456*log10(cao)) - 450
    Nữ  : 495 / (1.29579 - 0.35004*log10(eo + hông - cổ) + 0.22100*log10(cao)) - 450
    """
    if height_cm <= 0 or neck_cm <= 0:
        raise ValueError("Số đo chiều cao và vòng cổ phải lớn hơn 0")

    if gender == "female":
        if not hip_cm or hip_cm <= 0:
            raise ValueError("Cần số đo vòng hông đối với nữ giới")
        circumference = waist_cm + hip_cm - neck_cm
        if circumference <= 0:
            raise ValueError("Số đo vòng không hợp lệ (eo + hông - cổ phải > 0)")
        denominator = (
            1.29579
            - 0.35004 * math.log10(circumference)
            + 0.22100 * math.log10(height_cm)
        )
    else:
        circumference = waist_cm - neck_cm
        if circumference <= 0:
            raise ValueError("Vòng eo phải lớn hơn vòng cổ")
        denominator = (
            1.0324
            - 0.19077 * math.log10(circumference)
            + 0.15456 * math.log10(height_cm)
        )

    if denominator <= 0:
        raise ValueError("Số đo không hợp lệ, không thể ước tính Body Fat")

    body_fat = (495.0 / denominator) - 450.0
    # Kẹp trong khoảng sinh lý hợp lý
    return round(max(3.0, min(65.0, body_fat)), 1)


# --------------------------------------------------------------------------
# XẾP LOẠI THEO GIỚI TÍNH + ĐỘ TUỔI
# --------------------------------------------------------------------------
def _age_offset(age: Optional[int]) -> float:
    """Người lớn tuổi có tỷ lệ mỡ nền cao hơn tự nhiên (~1%/thập kỷ sau 30)."""
    if not age or age <= 30:
        return 0.0
    decades = (age - 30) / 10.0
    return round(decades * 1.0, 2)


def classify_body_fat(gender: str, body_fat_pct: float, age: Optional[int] = None) -> str:
    """Trả về nhóm phân loại Body Fat: Essential/Athletes/Fitness/Average/Obese.

    Các dải trong BODY_FAT_RANGES được nêu dưới dạng số nguyên (Fitness 14-17%,
    Average 18-24%, Obese >=25%) nên tồn tại khe hở giữa các dải (17.5%).
    Hàm này coi mỗi nhóm trải liên tục từ cận dưới của nó tới NGAY TRƯỚC cận dưới
    của nhóm kế tiếp, nhờ đó giá trị nằm trong khe hở luôn được xếp vào nhóm thấp
    hơn — đúng với mô tả "Obese từ 25% trở lên".
    """
    ranges = BODY_FAT_RANGES.get("female" if gender == "female" else "male")
    adjusted = body_fat_pct - _age_offset(age)

    if adjusted < ranges[0][1]:
        return ranges[0][0]  # dưới ngưỡng mỡ thiết yếu tối thiểu

    for index, (label, _low, _high) in enumerate(ranges):
        next_low = ranges[index + 1][1] if index + 1 < len(ranges) else float("inf")
        if adjusted < next_low:
            return label

    return ranges[-1][0]  # Obese


def ffmi_interpretation(gender: str, ffmi_normalized: float) -> str:
    """Diễn giải FFMI (chuẩn hóa) — phản ánh lượng cơ nạc trên khung xương."""
    if gender == "female":
        if ffmi_normalized < 14:
            return "Rất ít cơ - Cần ưu tiên tập kháng lực ngay"
        if ffmi_normalized < 16:
            return "Cơ bắp dưới trung bình"
        if ffmi_normalized < 18:
            return "Cơ bắp trung bình khá"
        if ffmi_normalized < 20:
            return "Cơ bắp tốt - Thể hình săn chắc"
        return "Cơ bắp vượt trội (gần ngưỡng tự nhiên)"
    if ffmi_normalized < 18:
        return "Rất ít cơ - Cần ưu tiên tập kháng lực ngay"
    if ffmi_normalized < 20:
        return "Cơ bắp dưới trung bình"
    if ffmi_normalized < 22:
        return "Cơ bắp trung bình khá"
    if ffmi_normalized < 24:
        return "Cơ bắp tốt - Thể hình săn chắc"
    if ffmi_normalized < 26:
        return "Cơ bắp vượt trội (gần ngưỡng tự nhiên)"
    return "Cơ bắp cấp độ thi đấu / có can thiệp hỗ trợ"


def classify_body_type(
    bmi: float,
    body_fat_pct: float,
    body_fat_category: str,
    ffmi_normalized: float,
    gender: str,
) -> str:
    """Xác định tạng người hiện tại — trọng tâm là phát hiện 'Skinny Fat'.

    Skinny Fat = BMI bình thường (hoặc chỉ hơi cao) NHƯNG tỷ lệ mỡ cao
    và khối lượng cơ thấp.
    """
    low_muscle_threshold = 18.0 if gender != "female" else 14.5

    # Ưu tiên 1: Béo phì rõ ràng
    if body_fat_category == "Obese":
        return "obese"

    # Ưu tiên 2: Skinny Fat — ngoại hình không quá nặng nhưng mỡ nhiều, cơ ít
    if body_fat_pct >= (18.0 if gender != "female" else 25.0) and (
        bmi < 27.0 or ffmi_normalized < low_muscle_threshold
    ):
        return "skinny_fat"

    # Ưu tiên 3: Thể trạng vận động viên
    if body_fat_category in ("Essential", "Athletes") and ffmi_normalized >= (
        20.0 if gender != "female" else 16.0
    ):
        return "athletic"

    # Ưu tiên 4: Thừa cân nhưng chưa béo phì
    if bmi >= 25.0:
        return "overweight"

    # Ưu tiên 5: Gầy
    if bmi < 18.5 or ffmi_normalized < low_muscle_threshold:
        return "skinny"

    # Ưu tiên 6: Gọn gàng ít mỡ nhưng cơ chưa nổi bật
    if body_fat_category in ("Athletes", "Fitness"):
        return "lean"

    return "average"


def _muscle_quality(body_fat_category: str, ffmi_normalized: float, gender: str) -> str:
    """Chất lượng cơ - mỡ tổng hợp, dùng cho phần nhận định."""
    good_muscle = ffmi_normalized >= (20.0 if gender != "female" else 16.0)
    good_fat = body_fat_category in ("Essential", "Athletes", "Fitness")
    if good_muscle and good_fat:
        return "Xuất sắc - Cơ nạc cao và tỷ lệ mỡ trong vùng tối ưu"
    if good_muscle and not good_fat:
        return "Cơ tốt nhưng mỡ còn cao - Chỉ cần siết mỡ là hình thể sẽ rất nét"
    if not good_muscle and good_fat:
        return "Mỡ thấp nhưng thiếu cơ - Cần tăng khối lượng cơ để hình thể đầy đặn hơn"
    return "Cần cải thiện đồng thời cả cơ và mỡ"


# --------------------------------------------------------------------------
# LỘ TRÌNH & THỜI GIAN ĐẠT MỤC TIÊU
# --------------------------------------------------------------------------
def estimate_timeline(
    goal: str,
    weight_kg: float,
    fat_mass_kg: float,
    lean_body_mass_kg: float,
    gender: str,
) -> dict:
    """Tính mục tiêu mỡ/cơ cần thay đổi và số tuần an toàn để đạt được."""
    gender_key = "female" if gender == "female" else "male"
    target_bf = TARGET_BODY_FAT.get(goal, TARGET_BODY_FAT["recomp"])[gender_key]

    result = {
        "target_body_fat_percentage": target_bf,
        "fat_to_lose_kg": 0.0,
        "muscle_to_gain_kg": 0.0,
        "weekly_fat_loss_kg": 0.0,
        "estimated_weeks_to_goal": 0,
    }

    if goal in ("cutting", "recomp"):
        # Khối lượng cơ được giữ nguyên (mục tiêu vàng của Cutting)
        target_weight = lean_body_mass_kg / (1 - target_bf / 100.0)
        fat_to_lose = max(0.0, round(fat_mass_kg - (target_weight - lean_body_mass_kg), 1))
        result["fat_to_lose_kg"] = fat_to_lose

        # Tốc độ an toàn 0.5 - 1% trọng lượng cơ thể/tuần; thực tế lấy 0.75%
        weekly = round(weight_kg * 0.0075, 2)
        weekly = max(0.25, weekly)
        result["weekly_fat_loss_kg"] = weekly
        weeks = math.ceil(fat_to_lose / weekly) if fat_to_lose > 0 else 0

        if goal == "recomp":
            # Recomp: tăng cơ song song, cộng thêm thời gian cho chu kỳ tăng cơ
            muscle_gain = round(weight_kg * 0.02, 1)
            result["muscle_to_gain_kg"] = muscle_gain
            weeks = max(weeks, math.ceil(muscle_gain / max(0.15, weight_kg * 0.0025)))

        result["estimated_weeks_to_goal"] = max(4, weeks)

    elif goal == "bulking":
        # Tăng cơ với tỷ lệ cơ/mỡ hợp lý (lean bulk)
        muscle_gain = round(lean_body_mass_kg * 0.08, 1)
        result["muscle_to_gain_kg"] = muscle_gain
        weekly = round(weight_kg * 0.0035, 2)
        result["weekly_fat_loss_kg"] = 0.0
        result["estimated_weeks_to_goal"] = max(
            8, math.ceil(muscle_gain / max(0.2, weekly))
        )

    else:  # endurance
        fat_to_lose = max(0.0, round(fat_mass_kg * 0.25, 1))
        result["fat_to_lose_kg"] = fat_to_lose
        weekly = max(0.25, round(weight_kg * 0.006, 2))
        result["weekly_fat_loss_kg"] = weekly
        result["estimated_weeks_to_goal"] = max(6, math.ceil(fat_to_lose / weekly))

    return result


def calc_water_intake(weight_kg: float, training_hours_per_week: int = 4) -> float:
    """Nước/ngày = Cân nặng x 0.04 (lít) + 500ml cho mỗi giờ tập luyện.

    Quy đổi phần tập luyện theo tuần thành mức trung bình mỗi ngày.
    """
    base = weight_kg * 0.04
    training_bonus = (training_hours_per_week * 0.5) / 7.0
    return round(base + training_bonus, 2)


def build_assessment_summary(
    gender: str,
    body_fat_pct: float,
    body_fat_category: str,
    body_type: str,
    bmi: float,
    ffmi_note: str,
    goal: str,
    timeline: dict,
) -> str:
    """Sinh nhận định chuyên môn thẳng thắn nhưng tích cực."""
    label = "nam" if gender != "female" else "nữ"
    parts: list[str] = []

    parts.append(
        f"Với tỷ lệ mỡ cơ thể {body_fat_pct}% ở {label} giới, bạn đang nằm ở nhóm "
        f"'{body_fat_category}' ({BODY_FAT_LABELS_VI.get(body_fat_category, '')})."
    )

    parts.append(f"Chỉ số BMI {bmi} cho thấy {bmi_category(bmi).lower()}.")

    if body_type == "skinny_fat":
        parts.append(
            "Đây là tạng người Skinny Fat điển hình: cân nặng trông bình thường "
            "nhưng tỷ lệ mỡ cao trong khi khối lượng cơ còn thấp. "
            "Sai lầm phổ biến là chỉ chạy cardio và ăn ít — cách đó sẽ làm mất thêm cơ. "
            "Chiến lược đúng là tập kháng lực (tạ) để kích thích giữ và xây cơ, "
            "kết hợp thâm hụt calo nhẹ và nạp đủ đạm."
        )
    elif body_type == "obese":
        parts.append(
            "Lượng mỡ thừa đang ở mức cần can thiệp nghiêm túc, đặc biệt là mỡ nội tạng "
            "ảnh hưởng tim mạch và chuyển hoá. Tin tốt: đây cũng là nhóm đạt kết quả "
            "nhanh nhất khi bắt đầu đúng cách — giai đoạn đầu có thể giảm 0.8-1% "
            "trọng lượng cơ thể mỗi tuần."
        )
    elif body_type == "athletic":
        parts.append(
            "Thể trạng của bạn đã ở mức rất tốt. Mục tiêu lúc này là tối ưu hoá "
            "chi tiết: siết nét các nhóm cơ nhỏ, cải thiện mật độ cơ và duy trì "
            "hiệu suất tập luyện."
        )
    elif body_type in ("skinny", "lean"):
        parts.append(
            "Bạn có nền mỡ thấp — lợi thế lớn để xây dựng hình thể. "
            "Việc cần làm là tăng khối lượng cơ qua tập kháng lực tăng tiến "
            "và nạp đủ năng lượng, tránh thâm hụt calo quá sâu."
        )
    elif body_type == "overweight":
        parts.append(
            "Bạn đang thừa cân ở mức trung bình. Kết hợp tập kháng lực để giữ cơ "
            "với thâm hụt calo vừa phải sẽ giúp giảm cân mà không bị chùng da "
            "hay tụt sức."
        )
    else:
        parts.append(
            "Thể trạng tổng thể ở mức trung bình — còn nhiều dư địa để cải thiện "
            "rõ rệt trong 3-6 tháng tới nếu tuân thủ đúng phác đồ."
        )

    parts.append(f"Đánh giá khối cơ: {ffmi_note}.")

    if goal in ("cutting", "recomp") and timeline["fat_to_lose_kg"] > 0:
        parts.append(
            f"Mục tiêu thực tế: giảm khoảng {timeline['fat_to_lose_kg']}kg mỡ để đạt "
            f"tỷ lệ mỡ {timeline['target_body_fat_percentage']}%, duy trì tốc độ an toàn "
            f"{timeline['weekly_fat_loss_kg']}kg/tuần — tương đương "
            f"~{timeline['estimated_weeks_to_goal']} tuần "
            f"({max(1, round(timeline['estimated_weeks_to_goal'] / 4.3, 1))} tháng)."
        )
    elif goal == "bulking":
        parts.append(
            f"Mục tiêu thực tế: tăng khoảng {timeline['muscle_to_gain_kg']}kg cơ nạc "
            f"trong ~{timeline['estimated_weeks_to_goal']} tuần với chế độ lean bulk "
            f"(kiểm soát mỡ tăng kèm ở mức tối thiểu)."
        )
    else:
        parts.append(
            f"Lộ trình dự kiến ~{timeline['estimated_weeks_to_goal']} tuần để đạt "
            f"tỷ lệ mỡ mục tiêu {timeline['target_body_fat_percentage']}%."
        )

    return " ".join(parts)


def build_warnings(
    weight_kg: float,
    height_cm: float,
    body_fat_pct: float,
    bmi: float,
    age: Optional[int],
    goal: str,
    injuries: Optional[list[str]] = None,
) -> list[str]:
    """Cảnh báo an toàn cá nhân hoá."""
    warnings: list[str] = []

    if bmi >= 30:
        warnings.append(
            "BMI từ 30 trở lên: nên tầm soát huyết áp, đường huyết và mỡ máu trước khi "
            "tập cường độ cao. Ưu tiên 4-6 tuần đầu với bài tập ít tác động lên khớp "
            "(xe đạp, bơi, đi bộ dốc) trước khi chuyển sang chạy bộ."
        )
    if bmi < 17.5:
        warnings.append(
            "BMI dưới 17.5 (thiếu cân đáng kể): cần đánh giá dinh dưỡng và sàng lọc "
            "rối loạn ăn uống trước khi áp dụng thâm hụt calo."
        )
    if body_fat_pct < 5 and goal != "female":
        warnings.append(
            "Tỷ lệ mỡ dưới 5% ở nam giới là vùng nguy hiểm cho nội tiết và miễn dịch. "
            "Không nên siết mỡ sâu hơn."
        )
    if body_fat_pct < 12 and goal == "cutting":
        warnings.append(
            "Tỷ lệ mỡ đã rất thấp, việc siết thêm sẽ ảnh hưởng hormone và hiệu suất tập. "
            "Khuyến nghị chuyển sang giai đoạn duy trì hoặc tăng cơ."
        )
    if age and age >= 55:
        warnings.append(
            "Trên 55 tuổi: cần khởi động kỹ 10-15 phút, tăng tải trọng từ từ và "
            "ưu tiên bài tập thăng bằng để phòng ngừa chấn thương."
        )
    if age and age < 18:
        warnings.append(
            "Dưới 18 tuổi: chỉ nên tập kháng lực với tạ nhẹ - trung bình dưới sự giám sát "
            "của HLV, tuyệt đối không áp dụng thâm hụt calo sâu."
        )
    if weight_kg / ((height_cm / 100) ** 2) > 0 and goal == "bulking" and bmi >= 27:
        warnings.append(
            "BMI đã ở mức thừa cân: chế độ bulking truyền thống sẽ làm tăng mỡ đáng kể. "
            "Nên chọn Body Recomposition (ăn ngang TDEE) thay vì tăng cân."
        )

    injury_notes = {
        "lower_back": "Đau lưng dưới: loại bỏ Deadlift/Good Morning tạ nặng, thay bằng "
                      "Romanian Deadlift nhẹ, Hip Thrust và bài tập core chống duỗi (Plank, Bird Dog).",
        "knee": "Đau khớp gối: hạn chế Squat sâu và nhảy, thay bằng Leg Press biên độ an toàn, "
                "Goblet Squat, tập cơ mông-đùi sau để giảm tải lên khớp gối.",
        "shoulder": "Đau khớp vai: tránh Overhead Press và Bench Press biên độ lớn, "
                    "thay bằng Landmine Press, tạ đơn trung lập, kèm bài tập xoay ngoài vai.",
        "wrist": "Đau cổ tay: dùng tạ đơn thay tạ đòn, đeo quấn cổ tay và hạn chế "
                 "bài tập chống đẩy trên nền cứng.",
        "hip": "Đau khớp hông: tránh Squat biên độ sâu và bước dài, ưu tiên "
               "bài tập ổn định hông và giãn cơ hông trước tập.",
    }
    for inj in injuries or []:
        if inj in injury_notes:
            warnings.append(injury_notes[inj])

    return warnings


# --------------------------------------------------------------------------
# HÀM TỔNG HỢP
# --------------------------------------------------------------------------
def run_full_diagnosis(
    height_cm: float,
    weight_kg: float,
    body_fat_percentage: float,
    gender: str = "male",
    age: Optional[int] = None,
    activity_level: str = "moderate",
    goal: str = "cutting",
    injuries: Optional[list[str]] = None,
    training_hours_per_week: int = 4,
) -> DiagnosisResult:
    """Chạy toàn bộ pipeline chẩn đoán và trả về DiagnosisResult."""
    bmi = calc_bmi(weight_kg, height_cm)
    lbm = calc_lean_body_mass(weight_kg, body_fat_percentage)
    fat_mass = round(weight_kg - lbm, 2)
    bmr = calc_bmr_katch_mcardle(lbm)
    tdee = calc_tdee(bmr, activity_level)
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)

    bf_category = classify_body_fat(gender, body_fat_percentage, age)
    ffmi, ffmi_norm = calc_ffmi(lbm, height_cm)
    ffmi_note = ffmi_interpretation(gender, ffmi_norm)
    muscle_quality = _muscle_quality(bf_category, ffmi_norm, gender)

    body_type = classify_body_type(
        bmi, body_fat_percentage, bf_category, ffmi_norm, gender
    )
    timeline = estimate_timeline(goal, weight_kg, fat_mass, lbm, gender)

    summary = build_assessment_summary(
        gender, body_fat_percentage, bf_category, body_type,
        bmi, ffmi_note, goal, timeline,
    )

    return DiagnosisResult(
        height_cm=height_cm,
        weight_kg=weight_kg,
        body_fat_percentage=body_fat_percentage,
        age=age,
        gender=gender,
        bmi=bmi,
        bmi_category=bmi_category(bmi),
        lean_body_mass_kg=lbm,
        fat_mass_kg=fat_mass,
        bmr_kcal=bmr,
        tdee_kcal=tdee,
        activity_multiplier=multiplier,
        body_fat_category=bf_category,
        body_fat_category_vi=BODY_FAT_LABELS_VI.get(bf_category, ""),
        ffmi=ffmi,
        ffmi_normalized=ffmi_norm,
        ffmi_interpretation=ffmi_note,
        muscle_quality=muscle_quality,
        body_type=body_type,
        body_type_vi=BODY_TYPES.get(body_type, ""),
        ai_assessment_summary=summary,
        estimated_weeks_to_goal=timeline["estimated_weeks_to_goal"],
        target_body_fat_percentage=timeline["target_body_fat_percentage"],
        fat_to_lose_kg=timeline["fat_to_lose_kg"],
        muscle_to_gain_kg=timeline["muscle_to_gain_kg"],
        weekly_fat_loss_kg=timeline["weekly_fat_loss_kg"],
        warnings=build_warnings(
            weight_kg, height_cm, body_fat_percentage, bmi, age, goal, injuries
        ),
        water_min_liters=calc_water_intake(weight_kg, training_hours_per_week),
    )