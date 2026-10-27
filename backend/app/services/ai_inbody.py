"""INBODY ANALYSIS ENGINE — Phân tích thành phần cơ thể chuyên sâu.

Nghiệp vụ:
    1. Chỉ số tổng thể: SMM (khối cơ xương), BFM (khối mỡ), mỡ nội tạng,
       nước, protein, khoáng, WHR.
    2. Phân tích cơ - mỡ TỪNG VÙNG (Segmental Lean/Fat): tay trái/phải,
       thân mình, chân trái/phải.
    3. Phát hiện MẤT CÂN BẰNG cơ bắp -> AI bổ sung bài tập đơn bên (unilateral).
    4. Chẩn đoán DẠNG HÌNH THỂ C-I-D:
         C = Skinny Fat (thừa mỡ thiếu cơ)  -> Recomp hoặc thâm hụt nhẹ + tập tạ
         I = Cân đối                        -> Bulking hoặc Cutting theo mục tiêu
         D = Vận động viên / cơ vượt trội   -> Tối ưu hiệu suất và độ nét cơ
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------
# NGƯỠNG CHUẨN LÂM SÀNG
# --------------------------------------------------------------------------
#: Mức mỡ nội tạng: < 10 là chuẩn, >= 10 là cảnh báo
VISCERAL_FAT_NORMAL_MAX = 10.0

#: Chỉ số WHR (Waist-Hip Ratio) nguy cơ tim mạch theo WHO
WHR_RISK_THRESHOLD = {"male": 0.90, "female": 0.85}

#: Ngưỡng chênh lệch % giữa 2 bên để coi là mất cân bằng
IMBALANCE_THRESHOLD_PERCENT = 5.0
#: Ngưỡng chênh lệch thân trên vs thân dưới
UPPER_LOWER_IMBALANCE_PERCENT = 12.0

#: Tỷ lệ SMM/Weight tối thiểu theo giới tính (chỉ số sức mạnh cơ)
MIN_SMM_RATIO = {"male": 0.40, "female": 0.33}


class ShapeType:
    """Dạng hình thể theo InBody."""

    C_SHAPE = "C"   # Skinny Fat
    I_SHAPE = "I"   # Cân đối
    D_SHAPE = "D"   # Vận động viên

    LABELS = {
        C_SHAPE: "Dạng chữ C — Skinny Fat (Thừa mỡ, thiếu cơ)",
        I_SHAPE: "Dạng chữ I — Cân đối",
        D_SHAPE: "Dạng chữ D — Vận động viên / Cơ bắp vượt trội",
    }


@dataclass
class SegmentalAnalysis:
    """Kết quả phân tích vùng."""

    lean_left_arm: Optional[float] = None
    lean_right_arm: Optional[float] = None
    lean_trunk: Optional[float] = None
    lean_left_leg: Optional[float] = None
    lean_right_leg: Optional[float] = None

    fat_left_arm: Optional[float] = None
    fat_right_arm: Optional[float] = None
    fat_trunk: Optional[float] = None
    fat_left_leg: Optional[float] = None
    fat_right_leg: Optional[float] = None

    arm_difference_kg: float = 0.0
    arm_difference_percent: float = 0.0
    leg_difference_kg: float = 0.0
    leg_difference_percent: float = 0.0
    trunk_to_limb_ratio: float = 0.0
    balance_score: float = 100.0
    imbalances: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    has_data: bool = False


@dataclass
class InBodyResult:
    """Kết quả phân tích InBody đầy đủ."""

    shape_type: str
    shape_description: str
    shape_rationale: str

    visceral_fat_level: Optional[float]
    visceral_fat_status: str
    whr: Optional[float]
    whr_status: Optional[str]
    smm_ratio: Optional[float]
    smm_ratio_status: Optional[str]

    segmental: SegmentalAnalysis
    priority_actions: list[str] = field(default_factory=list)
    goal_recommendation: str = ""
    training_adjustments: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""


def _pct_diff(a: Optional[float], b: Optional[float]) -> tuple[float, float]:
    """Chênh lệch tuyệt đối và % giữa 2 giá trị."""
    if a is None or b is None:
        return 0.0, 0.0
    diff = abs(a - b)
    base = (a + b) / 2
    if base <= 0:
        return round(diff, 2), 0.0
    return round(diff, 2), round(diff / base * 100, 1)


def analyze_segmental(
    lean_left_arm: Optional[float],
    lean_right_arm: Optional[float],
    lean_trunk: Optional[float],
    lean_left_leg: Optional[float],
    lean_right_leg: Optional[float],
    fat_left_arm: Optional[float] = None,
    fat_right_arm: Optional[float] = None,
    fat_trunk: Optional[float] = None,
    fat_left_leg: Optional[float] = None,
    fat_right_leg: Optional[float] = None,
) -> SegmentalAnalysis:
    """Phân tích cơ - mỡ từng vùng và phát hiện mất cân bằng."""
    result = SegmentalAnalysis(
        lean_left_arm=lean_left_arm, lean_right_arm=lean_right_arm,
        lean_trunk=lean_trunk, lean_left_leg=lean_left_leg, lean_right_leg=lean_right_leg,
        fat_left_arm=fat_left_arm, fat_right_arm=fat_right_arm,
        fat_trunk=fat_trunk, fat_left_leg=fat_left_leg, fat_right_leg=fat_right_leg,
    )

    has_lean = any(
        v is not None for v in
        (lean_left_arm, lean_right_arm, lean_trunk, lean_left_leg, lean_right_leg)
    )
    result.has_data = has_lean
    if not has_lean:
        result.recommendations.append(
            "Chưa có dữ liệu phân tích vùng. Nhập đủ 5 vùng từ phiếu InBody để "
            "AI phát hiện mất cân bằng cơ bắp."
        )
        return result

    penalty = 0.0

    # --- 1. So sánh tay trái vs tay phải ---
    arm_diff, arm_pct = _pct_diff(lean_left_arm, lean_right_arm)
    result.arm_difference_kg = arm_diff
    result.arm_difference_percent = arm_pct

    if arm_pct >= IMBALANCE_THRESHOLD_PERCENT and arm_diff > 0:
        weaker = "trái" if (lean_left_arm or 0) < (lean_right_arm or 0) else "phải"
        stronger = "phải" if weaker == "trái" else "trái"
        result.imbalances.append({
            "type": "arm_asymmetry",
            "severity": "high" if arm_pct >= 10 else "medium",
            "difference_kg": arm_diff,
            "difference_percent": arm_pct,
            "detail": f"Tay {weaker} yếu hơn tay {stronger} {arm_diff}kg ({arm_pct}%)",
        })
        result.recommendations.append(
            f"MẤT CÂN BẰNG TAY: tay {weaker} nhỏ hơn tay {stronger} {arm_pct}%. "
            f"Bổ sung bài tập ĐƠN BÊN (unilateral) với tạ đơn: One-arm Dumbbell Row, "
            f"Single-arm Dumbbell Curl, Single-arm Triceps Extension, "
            f"và luôn bắt đầu bằng bên {weaker} yếu hơn."
        )
        result.recommendations.append(
            f"Nguyên tắc sửa mất cân bằng: tập bên yếu trước, bên khỏe chỉ tập đúng "
            f"số reps mà bên yếu hoàn thành được (không tập thêm)."
        )
        penalty += min(arm_pct * 1.5, 20)

    # --- 2. So sánh chân trái vs chân phải ---
    leg_diff, leg_pct = _pct_diff(lean_left_leg, lean_right_leg)
    result.leg_difference_kg = leg_diff
    result.leg_difference_percent = leg_pct

    if leg_pct >= IMBALANCE_THRESHOLD_PERCENT and leg_diff > 0:
        weaker = "trái" if (lean_left_leg or 0) < (lean_right_leg or 0) else "phải"
        stronger = "phải" if weaker == "trái" else "trái"
        result.imbalances.append({
            "type": "leg_asymmetry",
            "severity": "high" if leg_pct >= 10 else "medium",
            "difference_kg": leg_diff,
            "difference_percent": leg_pct,
            "detail": f"Chân {weaker} yếu hơn chân {stronger} {leg_diff}kg ({leg_pct}%)",
        })
        result.recommendations.append(
            f"MẤT CÂN BẰNG CHÂN: chân {weaker} nhỏ hơn chân {stronger} {leg_pct}%. "
            f"Bổ sung: Single-leg Press, Bulgarian Split Squat, Step-up, "
            f"Single-leg Romanian Deadlift. Bắt đầu bằng chân {weaker}."
        )
        result.recommendations.append(
            "Kiểm tra lại tư thế đứng và dáng đi — mất cân bằng chân thường liên quan "
            "tới lệch khung chậu hoặc thói quen dồn lực một bên."
        )
        penalty += min(leg_pct * 1.5, 20)

    # --- 3. So sánh thân trên vs thân dưới ---
    if lean_trunk is not None and lean_left_leg is not None and lean_right_leg is not None:
        legs_avg = ((lean_left_leg or 0) + (lean_right_leg or 0)) / 2
        arms_avg = (
            ((lean_left_arm or 0) + (lean_right_arm or 0)) / 2
            if lean_left_arm is not None and lean_right_arm is not None
            else None
        )
        if legs_avg > 0 and lean_trunk:
            # Tỷ lệ thân mình / chân — giá trị tham chiếu cân đối ~2.2-2.8
            ratio = round(lean_trunk / legs_avg, 2)
            result.trunk_to_limb_ratio = ratio

            if ratio < 2.0:
                result.imbalances.append({
                    "type": "lower_body_dominant",
                    "severity": "medium",
                    "detail": f"Chân phát triển tốt so với thân trên (tỷ lệ {ratio})",
                })
                result.recommendations.append(
                    f"Thân trên còn mỏng so với chân (tỷ lệ thân/chân = {ratio}). "
                    f"Ưu tiên tăng volume cho ngực, xô, vai và tay."
                )
                penalty += 6
            elif ratio > 3.0:
                result.imbalances.append({
                    "type": "upper_body_dominant",
                    "severity": "high",
                    "detail": f"Thân trên phát triển hơn chân rõ rệt (tỷ lệ {ratio})",
                })
                result.recommendations.append(
                    f"CHÂN YẾU HƠN THÂN TRÊN rõ rệt (tỷ lệ thân/chân = {ratio}). "
                    f"Đây là mất cân bằng cần ưu tiên sửa: tăng lên 2 buổi chân/tuần, "
                    f"tập compound chân trước trong buổi, và không bỏ buổi chân."
                )
                penalty += 12

        # Nhận xét tay
        if arms_avg is not None and arms_avg > 0 and legs_avg / arms_avg > 4.5:
            result.recommendations.append(
                "Tay khá nhỏ so với chân — bổ sung thêm volume cho tay trước và tay sau."
            )
            penalty += 4

    # --- 4. Mỡ tập trung ở thân mình ---
    if fat_trunk is not None and fat_left_leg is not None and fat_right_leg is not None:
        fat_limbs = fat_left_leg + fat_right_leg
        if fat_left_arm is not None and fat_right_arm is not None:
            fat_limbs += fat_left_arm + fat_right_arm
        if fat_limbs > 0 and fat_trunk / fat_limbs > 1.6:
            result.imbalances.append({
                "type": "central_fat_accumulation",
                "severity": "medium",
                "detail": "Mỡ tập trung chủ yếu ở vùng thân mình (bụng, eo)",
            })
            result.recommendations.append(
                "Mỡ tập trung ở thân mình (dạng tích mỡ trung tâm) — liên quan tới mỡ nội "
                "tạng và nguy cơ chuyển hoá. Ưu tiên thâm hụt calo, tăng vận động NEAT "
                "và giảm stress/cortisol. Không thể giảm mỡ cục bộ bằng bài tập bụng."
            )
            penalty += 8

    result.balance_score = round(max(0.0, 100.0 - penalty), 1)

    if not result.imbalances:
        result.recommendations.append(
            "Cơ thể cân đối tốt giữa các vùng — tiếp tục duy trì chương trình hiện tại."
        )

    return result


def detect_shape(
    body_fat_percentage: Optional[float],
    smm_ratio: Optional[float],
    gender: str,
    ffmi_normalized: Optional[float] = None,
) -> tuple[str, str]:
    """Chẩn đoán dạng hình thể C / I / D.

    Tiêu chí:
        C (Skinny Fat): tỷ lệ mỡ cao + khối cơ thấp/trung bình
        D (Vận động viên): khối cơ cao + tỷ lệ mỡ thấp
        I (Cân đối): các trường hợp còn lại

    Trả về (shape_code, lý do).
    """
    is_female = gender == "female"

    # Ngưỡng mỡ cao/thấp theo giới tính
    high_fat = (body_fat_percentage or 0) >= (32.0 if is_female else 25.0)
    low_fat = (body_fat_percentage or 100) <= (24.0 if is_female else 15.0)

    # Ngưỡng khối cơ theo tỷ lệ SMM/Weight
    min_ratio = MIN_SMM_RATIO["female" if is_female else "male"]
    low_muscle = smm_ratio is not None and smm_ratio < min_ratio
    high_muscle = smm_ratio is not None and smm_ratio >= min_ratio + 0.06

    # FFMI là chỉ số dự phòng khi không có SMM
    if smm_ratio is None and ffmi_normalized is not None:
        low_muscle = ffmi_normalized < (14.5 if is_female else 18.0)
        high_muscle = ffmi_normalized >= (16.0 if is_female else 22.0)

    # --- D: cơ cao + mỡ thấp/trung bình ---
    if high_muscle and not high_fat:
        return (
            ShapeType.D_SHAPE,
            f"Khối cơ nạc cao (SMM/Weight = {smm_ratio}) kết hợp tỷ lệ mỡ "
            f"{body_fat_percentage}% ở mức tốt.",
        )

    # --- C: mỡ cao + cơ thấp/trung bình ---
    if high_fat and not high_muscle:
        return (
            ShapeType.C_SHAPE,
            f"Tỷ lệ mỡ {body_fat_percentage}% cao trong khi khối cơ còn thấp "
            f"(SMM/Weight = {smm_ratio}) — ngoại hình có thể bình thường nhưng "
            f"cơ thể thiếu cơ và thừa mỡ.",
        )

    # --- I: cân đối ---
    if low_muscle and low_fat:
        return (
            ShapeType.I_SHAPE,
            f"Khối cơ và tỷ lệ mỡ ({body_fat_percentage}%) đều ở mức trung bình — "
            f"cơ thể cân đối nhưng chưa nổi bật.",
        )

    return (
        ShapeType.I_SHAPE,
        f"Khối cơ (SMM/Weight = {smm_ratio}) và tỷ lệ mỡ ({body_fat_percentage}%) "
        f"ở mức cân đối.",
    )


def analyze_inbody(
    *,
    height_cm: Optional[float] = None,
    weight_kg: Optional[float] = None,
    body_fat_percentage: Optional[float] = None,
    skeletal_muscle_mass_kg: Optional[float] = None,
    body_fat_mass_kg: Optional[float] = None,
    visceral_fat_level: Optional[float] = None,
    waist_cm: Optional[float] = None,
    hip_cm: Optional[float] = None,
    gender: str = "male",
    age: Optional[int] = None,
    lean_left_arm: Optional[float] = None,
    lean_right_arm: Optional[float] = None,
    lean_trunk: Optional[float] = None,
    lean_left_leg: Optional[float] = None,
    lean_right_leg: Optional[float] = None,
    fat_left_arm: Optional[float] = None,
    fat_right_arm: Optional[float] = None,
    fat_trunk: Optional[float] = None,
    fat_left_leg: Optional[float] = None,
    fat_right_leg: Optional[float] = None,
) -> InBodyResult:
    """Chạy phân tích InBody đầy đủ."""
    is_female = gender == "female"

    # --- Tỷ lệ SMM / cân nặng ---
    smm_ratio = None
    smm_ratio_status = None
    if skeletal_muscle_mass_kg and weight_kg:
        smm_ratio = round(skeletal_muscle_mass_kg / weight_kg, 3)
        threshold = MIN_SMM_RATIO["female" if is_female else "male"]
        if smm_ratio < threshold:
            smm_ratio_status = (
                f"THẤP (dưới ngưỡng {threshold}) — khối cơ chưa đủ so với cân nặng"
            )
        elif smm_ratio < threshold + 0.05:
            smm_ratio_status = f"Trung bình (ngưỡng chuẩn {threshold})"
        else:
            smm_ratio_status = "TỐT — khối cơ cao so với cân nặng"

    # --- Mỡ nội tạng ---
    visceral_status = "Chưa có dữ liệu"
    if visceral_fat_level is not None:
        if visceral_fat_level < 10:
            visceral_status = "Chuẩn (dưới 10) — nguy cơ chuyển hoá thấp"
        elif visceral_fat_level < 15:
            visceral_status = "CẢNH BÁO (10-14) — mỡ nội tạng cao, cần giảm"
        else:
            visceral_status = "NGUY HIỂM (từ 15) — nguy cơ tim mạch và tiểu đường cao"

    # --- WHR ---
    whr = None
    whr_status = None
    if waist_cm and hip_cm and hip_cm > 0:
        whr = round(waist_cm / hip_cm, 3)
        limit = WHR_RISK_THRESHOLD["female" if is_female else "male"]
        whr_status = (
            f"Trong ngưỡng an toàn (dưới {limit})" if whr < limit
            else f"VƯỢT NGƯỠNG NGUY CƠ (từ {limit}) — tích mỡ trung tâm"
        )

    # --- FFMI dự phòng để chẩn đoán dạng hình ---
    ffmi_normalized = None
    if weight_kg and height_cm and body_fat_percentage is not None:
        lbm = weight_kg * (1 - body_fat_percentage / 100)
        h_m = height_cm / 100
        if h_m > 0:
            ffmi_normalized = round(lbm / (h_m ** 2) + 6.1 * (1.8 - h_m), 2)

    shape_type, shape_rationale = detect_shape(
        body_fat_percentage, smm_ratio, gender, ffmi_normalized
    )
    shape_description = ShapeType.LABELS[shape_type]

    # --- Phân tích vùng ---
    segmental = analyze_segmental(
        lean_left_arm, lean_right_arm, lean_trunk, lean_left_leg, lean_right_leg,
        fat_left_arm, fat_right_arm, fat_trunk, fat_left_leg, fat_right_leg,
    )

    # --- Hành động ưu tiên & khuyến nghị mục tiêu theo dạng hình ---
    priority_actions: list[str] = []
    training_adjustments: list[str] = []
    warnings: list[str] = []

    if shape_type == ShapeType.C_SHAPE:
        goal_recommendation = "recomp"
        priority_actions.append(
            "Ưu tiên số 1: tập KHÁNG LỰC (tạ) 3-4 buổi/tuần — đây là yếu tố quyết định "
            "để tăng cơ và thoát khỏi tình trạng Skinny Fat."
        )
        priority_actions.append(
            "Dinh dưỡng: Body Recomposition (ăn ngang TDEE) hoặc thâm hụt rất nhẹ "
            "100-200 kcal, với đạm cao 2.0-2.2g/kg cân nặng."
        )
        priority_actions.append(
            "KHÔNG chạy cardio quá nhiều — cardio nhiều trong khi thiếu cơ sẽ làm mất "
            "thêm cơ và khiến tình trạng Skinny Fat nặng hơn."
        )
        training_adjustments.append(
            "Tập compound nặng trước (Squat, Deadlift, Bench, Row) với 6-10 reps để "
            "kích thích phát triển cơ tối đa."
        )
        training_adjustments.append(
            "Thêm 10-15 phút LISS sau buổi tập tạ (không thay thế buổi tạ)."
        )
        warnings.append(
            "Đừng đánh giá kết quả chỉ qua cân nặng — ở dạng C, cân nặng có thể không đổi "
            "nhưng tỷ lệ mỡ giảm và cơ tăng là thành công. Hãy theo dõi vòng eo và body fat."
        )

    elif shape_type == ShapeType.I_SHAPE:
        goal_recommendation = "recomp"
        priority_actions.append(
            "Cơ thể cân đối — bạn có thể chọn mục tiêu theo thẩm mỹ: "
            "Cutting để siết nét, hoặc Lean Bulking để tăng khối lượng cơ."
        )
        priority_actions.append(
            "Duy trì đạm 1.8-2.2g/kg và tập kháng lực 4 buổi/tuần với Progressive Overload."
        )
        training_adjustments.append(
            "Nếu chọn Cutting: thâm hụt 15-20% TDEE, giữ nguyên tạ nặng để bảo toàn cơ."
        )
        training_adjustments.append(
            "Nếu chọn Lean Bulking: thặng dư 10-15% TDEE, mục tiêu tăng 1-1.5kg/tháng."
        )

    else:  # D_SHAPE
        goal_recommendation = "cutting"
        priority_actions.append(
            "Thể trạng đã ở mức rất tốt — mục tiêu lúc này là TỐI ƯU chi tiết: "
            "siết nét nhóm cơ nhỏ, cải thiện mật độ cơ và duy trì hiệu suất."
        )
        priority_actions.append(
            "Tập trung vào bài isolation cho các nhóm cơ còn mờ: vai sau, tay sau, "
            "bắp chân, core — thay vì chỉ tập compound nặng."
        )
        training_adjustments.append(
            "Duy trì tạ nặng (RPE 7-8) để giữ khối cơ trong giai đoạn siết mỡ."
        )
        training_adjustments.append(
            "Thêm buổi Deload mỗi 6-8 tuần để tránh quá tải hệ thần kinh trung ương."
        )
        warnings.append(
            "Với khối cơ lớn, mỗi kg cân nặng có giá trị calo cao hơn — "
            "TDEE của bạn có thể cao hơn tính toán lý thuyết. Theo dõi thực tế để điều chỉnh."
        )

    # Cảnh báo mỡ nội tạng
    if visceral_fat_level is not None and visceral_fat_level >= VISCERAL_FAT_NORMAL_MAX:
        warnings.append(
            f"⚠️ Mỡ nội tạng ở mức {visceral_fat_level} (chuẩn < 10). Mỡ nội tạng cao "
            f"liên quan trực tiếp tới nguy cơ tim mạch, tiểu đường type 2 và gan nhiễm mỡ. "
            f"Đây là chỉ số cần ưu tiên cải thiện hơn cả cân nặng."
        )
        priority_actions.insert(
            0,
            "Ưu tiên giảm mỡ nội tạng: thâm hụt calo, tăng vận động NEAT hằng ngày, "
            "giảm đường tinh luyện và rượu bia, ngủ đủ giấc.",
        )

    if whr_status and "VƯỢT NGƯỠNG" in whr_status:
        warnings.append(
            f"⚠️ Tỷ lệ eo/hông (WHR) = {whr} vượt ngưỡng an toàn. "
            f"Đây là dấu hiệu tích mỡ trung tâm — cần ưu tiên giảm mỡ."
        )

    # --- Tóm tắt ---
    summary_parts = [f"Chẩn đoán dạng hình thể: {shape_description}."]
    if smm_ratio is not None:
        summary_parts.append(f"Khối cơ xương SMM/Weight = {smm_ratio} ({smm_ratio_status}).")
    if body_fat_percentage is not None:
        summary_parts.append(f"Tỷ lệ mỡ cơ thể {body_fat_percentage}%.")
    if visceral_fat_level is not None:
        summary_parts.append(f"Mỡ nội tạng mức {visceral_fat_level} — {visceral_status}.")
    if segmental.has_data:
        summary_parts.append(
            f"Điểm cân đối cơ thể: {segmental.balance_score}/100 "
            f"({len(segmental.imbalances)} điểm mất cân bằng được phát hiện)."
        )
    summary_parts.append(f"Lý do chẩn đoán: {shape_rationale}")

    return InBodyResult(
        shape_type=shape_type,
        shape_description=shape_description,
        shape_rationale=shape_rationale,
        visceral_fat_level=visceral_fat_level,
        visceral_fat_status=visceral_status,
        whr=whr,
        whr_status=whr_status,
        smm_ratio=smm_ratio,
        smm_ratio_status=smm_ratio_status,
        segmental=segmental,
        priority_actions=priority_actions,
        goal_recommendation=goal_recommendation,
        training_adjustments=training_adjustments,
        warnings=warnings,
        summary=" ".join(summary_parts),
    )