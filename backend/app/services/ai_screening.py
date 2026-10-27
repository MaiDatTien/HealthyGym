"""PAR-Q+ MEDICAL SCREENING ENGINE — Sàng lọc an toàn y tế.

Đây là "cổng chặn" bắt buộc: AI Workout Planner KHÔNG được sinh lịch tập nếu
chưa có kết quả sàng lọc. Mọi ràng buộc an toàn đều sinh ra dưới dạng
**contraindication codes** — mã cấm cụ thể mà planner phải tuân thủ tuyệt đối.

Nguyên tắc: an toàn sức khỏe > hiệu quả tập luyện. Khi có xung đột, luôn chọn
phương án an toàn hơn.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------
# MÃ CHỐNG CHỈ ĐỊNH (CONTRAINDICATION CODES)
# --------------------------------------------------------------------------
class Contraindication:
    """Các mã cấm — AI Workout Planner đọc để loại bài tập."""

    # --- Cột sống / lưng dưới ---
    NO_AXIAL_LOAD = "no_axial_load"
    """Cấm nén trục dọc cột sống nặng: Barbell Back Squat, Conventional Deadlift,
    Overhead Press tạ đòn, Good Morning."""

    NO_SPINAL_FLEXION_LOAD = "no_spinal_flexion_load"
    """Cấm gập cột sống dưới tải: Sit-up tạ, Cable Crunch nặng, Deadlift tròn lưng."""

    # --- Khớp gối / chi dưới ---
    NO_HIGH_IMPACT = "no_high_impact"
    """Cấm cardio chấn động: chạy bộ tốc độ cao, nhảy dây, plyometric, HIIT nhảy."""

    NO_DEEP_KNEE_FLEXION = "no_deep_knee_flexion"
    """Cấm gập gối sâu dưới tải: Squat sâu, Walking Lunge biên độ lớn, Leg Press sâu."""

    # --- Khớp vai ---
    NO_OVERHEAD_PRESS = "no_overhead_press"
    """Cấm đẩy qua đầu: Overhead Press, Push Press, Pull-up rộng."""

    NO_SHOULDER_EXTENSION_LOAD = "no_shoulder_extension_load"
    """Cấm duỗi vai dưới tải lớn: Bench Press biên độ lớn, Dumbbell Fly sâu, Dip."""

    # --- Tim mạch / hô hấp ---
    NO_MAX_INTENSITY = "no_max_intensity"
    """Cấm cường độ tối đa: HIIT all-out, 1RM test, sprint."""

    REQUIRE_MEDICAL_CLEARANCE = "require_medical_clearance"
    """Bắt buộc có xác nhận y khoa trước khi bắt đầu chương trình."""

    SUPERVISION_REQUIRED = "supervision_required"
    """Bắt buộc có HLV giám sát trực tiếp trong buổi tập."""

    # --- Thai kỳ / sau sinh ---
    PREGNANCY_MODIFIED = "pregnancy_modified"
    """Chương trình điều chỉnh cho thai kỳ: không nằm ngửa sau tam cá nguyệt 1,
    không nén bụng, không Valsalva, giữ nhịp tim vừa phải."""

    POSTPARTUM_CORE_PROTECTION = "postpartum_core_protection"
    """Sau sinh: tránh áp lực ổ bụng cao, ưu tiên phục hồi sàn chậu và core sâu."""

    # --- Khác ---
    NO_BLOOD_PRESSURE_SPIKE = "no_bp_spike"
    """Cấm bài gây tăng huyết áp đột ngột: nín thở rặn (Valsalva), tạ nặng thấp reps."""


#: Nhãn tiếng Việt cho từng mã cấm
CONTRAINDICATION_LABELS: dict[str, str] = {
    Contraindication.NO_AXIAL_LOAD:
        "Không nén trục dọc cột sống (tránh Squat/Deadlift tạ đòn nặng)",
    Contraindication.NO_SPINAL_FLEXION_LOAD:
        "Không gập cột sống dưới tải (tránh gập bụng có tạ)",
    Contraindication.NO_HIGH_IMPACT:
        "Không bài tập chấn động mạnh (tránh chạy nhanh, nhảy dây, plyometric)",
    Contraindication.NO_DEEP_KNEE_FLEXION:
        "Không gập gối sâu dưới tải",
    Contraindication.NO_OVERHEAD_PRESS:
        "Không đẩy tạ qua đầu",
    Contraindication.NO_SHOULDER_EXTENSION_LOAD:
        "Không duỗi vai biên độ lớn dưới tải",
    Contraindication.NO_MAX_INTENSITY:
        "Không tập cường độ tối đa",
    Contraindication.REQUIRE_MEDICAL_CLEARANCE:
        "Cần xác nhận của bác sĩ trước khi tập",
    Contraindication.SUPERVISION_REQUIRED:
        "Cần HLV giám sát trực tiếp",
    Contraindication.PREGNANCY_MODIFIED:
        "Chương trình điều chỉnh cho thai kỳ",
    Contraindication.POSTPARTUM_CORE_PROTECTION:
        "Bảo vệ core và sàn chậu sau sinh",
    Contraindication.NO_BLOOD_PRESSURE_SPIKE:
        "Tránh bài gây tăng huyết áp đột ngột",
}


# --------------------------------------------------------------------------
# DTO ĐẦU VÀO
# --------------------------------------------------------------------------
@dataclass
class ScreeningInput:
    """Dữ liệu sàng lọc PAR-Q+."""

    # 7 câu hỏi PAR-Q chuẩn
    q_heart_condition: bool = False
    q_chest_pain: bool = False
    q_dizziness: bool = False
    q_chronic_disease: bool = False
    q_bone_joint: bool = False
    q_medication: bool = False
    q_other_reason: bool = False

    # Chi tiết bệnh lý
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
    postpartum_months: Optional[int] = None
    other_conditions: Optional[str] = None
    current_medications: Optional[str] = None

    # Ngữ cảnh lâm sàng bổ sung
    age: Optional[int] = None
    bmi: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    gender: str = "male"


@dataclass
class ScreeningResult:
    """Kết quả sàng lọc."""

    risk_level: str                       # low | moderate | high
    needs_medical_clearance: bool
    contraindications: list[str] = field(default_factory=list)
    contraindication_labels: list[str] = field(default_factory=list)
    safe_exercise_notes: list[str] = field(default_factory=list)
    clearance_note: Optional[str] = None
    parq_positive: bool = False            # có bất kỳ câu PAR-Q nào = Có
    flags: list[str] = field(default_factory=list)   # cờ cảnh báo nội bộ


def run_parq_screening(data: ScreeningInput) -> ScreeningResult:
    """Chạy sàng lọc PAR-Q+ và sinh danh sách chống chỉ định.

    Quy tắc nghiệp vụ (hard rules theo yêu cầu dự án):
      - Thoát vị đĩa đệm / đau lưng dưới -> cấm nén trục + gập cột sống dưới tải
      - BMI >= 30 hoặc BF cao, hoặc đau khớp gối -> cấm cardio chấn động
      - Đau khớp vai / rách Rotator Cuff -> cấm đẩy qua đầu + duỗi vai nặng
      - Bệnh tim mạch / huyết áp / đau ngực -> cấm cường độ tối đa + cần y khoa
      - Thai kỳ / sau sinh -> chương trình điều chỉnh riêng
    """
    result = ScreeningResult(risk_level="low", needs_medical_clearance=False)

    # --- 1. Đánh giá 7 câu PAR-Q chuẩn ---
    parq_answers = [
        data.q_heart_condition, data.q_chest_pain, data.q_dizziness,
        data.q_chronic_disease, data.q_bone_joint, data.q_medication,
        data.q_other_reason,
    ]
    result.parq_positive = any(parq_answers)

    # --- 2. Tim mạch & hô hấp ---
    if data.has_heart_disease or data.q_heart_condition or data.q_chest_pain:
        result.needs_medical_clearance = True
        result.risk_level = "high"
        result.contraindications.append(Contraindication.NO_MAX_INTENSITY)
        result.contraindications.append(Contraindication.NO_BLOOD_PRESSURE_SPIKE)
        result.contraindications.append(Contraindication.REQUIRE_MEDICAL_CLEARANCE)
        result.contraindications.append(Contraindication.SUPERVISION_REQUIRED)
        result.safe_exercise_notes.append(
            "Bắt đầu với cường độ rất nhẹ (RPE 3-4), tăng dần qua nhiều tuần. "
            "Dừng tập ngay và liên hệ y tế nếu thấy đau ngực, khó thở, chóng mặt hoặc "
            "tim đập bất thường."
        )
        result.safe_exercise_notes.append(
            "Ưu tiên cardio vùng nhịp tim thấp (Zone 2, 50-60% HRmax) và tập kháng lực "
            "nhẹ với nhiều lần lặp. Không nín thở khi gắng sức (tránh Valsalva)."
        )
        result.flags.append("cardiovascular_risk")

    if data.has_hypertension or (data.q_chronic_disease and data.has_hypertension):
        result.needs_medical_clearance = True
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        if Contraindication.NO_BLOOD_PRESSURE_SPIKE not in result.contraindications:
            result.contraindications.append(Contraindication.NO_BLOOD_PRESSURE_SPIKE)
        result.safe_exercise_notes.append(
            "Huyết áp cao: tránh nín thở rặn khi nâng tạ. Thở ra ở pha gắng sức, "
            "dùng tạ trung bình với 10-15 lần lặp thay vì tạ nặng 1-5 lần. "
            "Theo dõi huyết áp trước và sau mỗi buổi tập."
        )
        result.flags.append("hypertension")

    if data.has_asthma:
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.safe_exercise_notes.append(
            "Hen suyễn: khởi động kéo dài 10-15 phút, luôn mang theo thuốc xịt dự phòng, "
            "tránh tập trong môi trường lạnh khô hoặc không khí kém. "
            "Ưu tiên bài tập ngắt quãng ngắn hơn là cardio liên tục dài."
        )
        result.flags.append("asthma")

    if data.has_diabetes:
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.safe_exercise_notes.append(
            "Tiểu đường: kiểm tra đường huyết trước buổi tập, mang theo nguồn carb nhanh "
            "(kẹo, nước ngọt). Tránh tập lúc đường huyết quá thấp hoặc quá cao. "
            "Chú ý chăm sóc bàn chân và mang giày phù hợp."
        )
        result.flags.append("diabetes")

    if data.q_dizziness:
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.safe_exercise_notes.append(
            "Có triệu chứng chóng mặt/mất thăng bằng: ưu tiên bài tập có điểm tựa, "
            "tránh thay đổi tư thế đột ngột. Cần được đánh giá y khoa trước khi tập nặng."
        )
        result.needs_medical_clearance = True
        result.flags.append("dizziness")

    # --- 3. Cột sống / thoát vị đĩa đệm ---
    if data.has_herniated_disc:
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.contraindications.append(Contraindication.NO_AXIAL_LOAD)
        result.contraindications.append(Contraindication.NO_SPINAL_FLEXION_LOAD)
        location = f" ({data.disc_levels})" if data.disc_levels else ""
        result.safe_exercise_notes.append(
            f"Thoát vị đĩa đệm{location}: TUYỆT ĐỐI tránh Barbell Back Squat và "
            f"Conventional Deadlift (nén trục dọc cột sống nặng). "
            f"Thay bằng: Belt Squat, Leg Press, Goblet Squat, Hip Thrust, "
            f"Romanian Deadlift tạ nhẹ, Hyperextension giữ lưng thẳng."
        )
        result.safe_exercise_notes.append(
            "Tập trung vào core chống duỗi và chống xoay: Plank, Dead Bug, Bird Dog. "
            "Tránh gập bụng có tải và mọi động tác xoay người dưới tạ."
        )
        result.flags.append("herniated_disc")

    if data.has_cervical_degeneration:
        result.contraindications.append(Contraindication.NO_AXIAL_LOAD)
        result.contraindications.append(Contraindication.NO_OVERHEAD_PRESS)
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.safe_exercise_notes.append(
            "Thoái hóa đốt sống cổ: tránh tải trực tiếp lên đỉnh đầu và đẩy qua đầu. "
            "Giữ cổ trung lập, không ưỡn cổ khi tập vai/ngực. "
            "Bổ sung bài tập cơ sâu vùng cổ-vai và giãn cơ thang."
        )
        result.flags.append("cervical_degeneration")

    # --- 4. Chi dưới / khớp gối / dây chằng ---
    if data.has_acl_tear or (data.q_bone_joint and data.has_acl_tear):
        result.contraindications.append(Contraindication.NO_HIGH_IMPACT)
        result.contraindications.append(Contraindication.NO_DEEP_KNEE_FLEXION)
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.safe_exercise_notes.append(
            "Đứt/rách dây chằng chéo (ACL): TUYỆT ĐỐI tránh nhảy, đổi hướng đột ngột, "
            "chạy nước rút và các bài plyometric. "
            "Tập trung phục hồi cơ tứ đầu, đùi sau và cơ mông để ổn định khớp gối."
        )
        result.flags.append("acl_tear")

    if data.q_bone_joint and not data.has_acl_tear:
        # Đau khớp nói chung -> hạn chế chấn động và gập sâu
        result.contraindications.append(Contraindication.NO_HIGH_IMPACT)
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.safe_exercise_notes.append(
            "Có vấn đề xương khớp: ưu tiên bài tập ít tác động lên khớp "
            "(xe đạp, elliptical, bơi, đi bộ dốc) và khởi động kỹ trước khi tập."
        )
        result.flags.append("joint_issue")

    # --- 5. Khớp vai ---
    if data.has_rotator_cuff:
        result.contraindications.append(Contraindication.NO_OVERHEAD_PRESS)
        result.contraindications.append(Contraindication.NO_SHOULDER_EXTENSION_LOAD)
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.safe_exercise_notes.append(
            "Đau khớp vai / Rotator Cuff: tránh đẩy tạ qua đầu và Bench Press biên độ lớn. "
            "Thay bằng: Landmine Press, đẩy tạ đơn tư thế trung lập, Cable Chest Fly "
            "biên độ an toàn. Bắt buộc thêm bài tập xoay ngoài vai (Face Pull, "
            "External Rotation) vào mỗi buổi tập thân trên."
        )
        result.flags.append("rotator_cuff")

    # --- 6. Thai kỳ & sau sinh ---
    if data.is_pregnant:
        result.contraindications.append(Contraindication.PREGNANCY_MODIFIED)
        result.needs_medical_clearance = True
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.safe_exercise_notes.append(
            "Thai kỳ: BẮT BUỘC có sự đồng ý của bác sĩ sản khoa trước khi tập. "
            "Không nằm ngửa sau tam cá nguyệt thứ nhất, không nén bụng, "
            "không nín thở rặn, giữ nhịp tim ở mức trò chuyện được. "
            "Tránh bài tập có nguy cơ té ngã và môn thể thao va chạm."
        )
        result.safe_exercise_notes.append(
            "Ưu tiên: đi bộ, bơi lội, xe đạp tĩnh, tập kháng lực nhẹ với dây kháng lực, "
            "bài tập sàn chậu (Kegel) và ổn định core."
        )
        result.flags.append("pregnancy")

    if data.postpartum_months is not None and data.postpartum_months <= 12:
        result.contraindications.append(Contraindication.POSTPARTUM_CORE_PROTECTION)
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.safe_exercise_notes.append(
            f"Sau sinh {data.postpartum_months} tháng: tránh bài tập gây áp lực ổ bụng cao "
            f"(gập bụng, plank nặng, nâng tạ nặng) cho tới khi sàn chậu hồi phục. "
            f"Ưu tiên bài tập hô hấp cơ hoành, kích hoạt cơ sàn chậu và core sâu. "
            f"Nên được đánh giá bởi chuyên gia vật lý trị liệu sàn chậu."
        )
        result.flags.append("postpartum")

    # --- 7. Béo phì độ II trở lên -> cấm cardio chấn động ---
    obesity_by_bmi = data.bmi is not None and data.bmi >= 30
    #: Ngưỡng Body Fat theo giới tính (nam > 30%, nữ > 38%)
    obesity_by_fat = (
        data.body_fat_percentage is not None
        and (
            (data.gender == "female" and data.body_fat_percentage > 38)
            or (data.gender != "female" and data.body_fat_percentage > 30)
        )
    )

    if obesity_by_bmi or obesity_by_fat:
        if Contraindication.NO_HIGH_IMPACT not in result.contraindications:
            result.contraindications.append(Contraindication.NO_HIGH_IMPACT)
        if Contraindication.NO_DEEP_KNEE_FLEXION not in result.contraindications:
            result.contraindications.append(Contraindication.NO_DEEP_KNEE_FLEXION)

        bmi_txt = f"BMI {data.bmi}" if data.bmi is not None else ""
        fat_txt = (
            f"Body Fat {data.body_fat_percentage}%"
            if data.body_fat_percentage is not None else ""
        )
        detail = " / ".join(x for x in (bmi_txt, fat_txt) if x)
        result.safe_exercise_notes.append(
            f"Béo phì độ II trở lên ({detail}): TUYỆT ĐỐI tránh chạy bộ tốc độ cao, "
            f"nhảy dây và HIIT nhảy cao để bảo vệ sụn khớp gối và cột sống. "
            f"Chuyển sang cardio KHÔNG CHẤN ĐỘNG (LISS): đi bộ dốc trên máy, "
            f"đạp xe tĩnh, bơi lội, máy elliptical. "
            f"4-6 tuần đầu chỉ dùng bài ít tác động, sau đó mới nâng dần cường độ."
        )
        if result.risk_level == "low":
            result.risk_level = "moderate"
        result.flags.append("obesity_grade_2")

    # --- 8. Các câu PAR-Q còn lại ---
    if data.q_other_reason and not result.contraindications:
        result.risk_level = "high" if result.risk_level == "high" else "moderate"
        result.safe_exercise_notes.append(
            "Bạn có lý do sức khỏe khác cần lưu ý: nên tham khảo ý kiến bác sĩ trước khi "
            "bắt đầu chương trình tập luyện."
        )
        result.flags.append("other_medical_reason")

    if data.q_medication:
        result.safe_exercise_notes.append(
            "Đang dùng thuốc điều trị: một số thuốc (chẹn beta, lợi tiểu, hạ đường huyết) "
            "ảnh hưởng tới nhịp tim, huyết áp và khả năng điều nhiệt khi tập. "
            "Hãy cho HLV biết loại thuốc đang dùng."
        )
        if result.risk_level == "low":
            result.risk_level = "moderate"
        result.flags.append("on_medication")

    # --- 9. Người cao tuổi ---
    if data.age and data.age >= 65:
        result.contraindications.append(Contraindication.SUPERVISION_REQUIRED)
        result.safe_exercise_notes.append(
            "Trên 65 tuổi: bắt buộc khởi động 10-15 phút, thêm bài tập thăng bằng "
            "(Single-leg Stand, Heel-to-toe Walk) vào mỗi buổi để phòng ngã. "
            "Tăng tải trọng rất chậm và ưu tiên duy trì khối cơ."
        )
        if result.risk_level == "low":
            result.risk_level = "moderate"
        result.flags.append("senior")

    # --- 10. Kết luận ---
    result.contraindications = sorted(set(result.contraindications))
    result.contraindication_labels = [
        CONTRAINDICATION_LABELS.get(c, c) for c in result.contraindications
    ]

    if result.needs_medical_clearance:
        result.clearance_note = (
            "⚠️ BẮT BUỘC: Bạn cần được bác sĩ khám và xác nhận đủ điều kiện sức khỏe "
            "trước khi bắt đầu chương trình tập luyện này. Vui lòng xuất trình giấy "
            "xác nhận cho phòng gym. Phác đồ dưới đây chỉ mang tính tham khảo cho tới khi "
            "có xác nhận y khoa."
        )
    elif result.risk_level == "moderate":
        result.clearance_note = (
            "ℹ️ Bạn ở mức rủi ro trung bình. Nên tham khảo ý kiến bác sĩ trước khi bắt đầu "
            "và nên tập dưới sự hướng dẫn của HLV trong 2-4 tuần đầu."
        )

    return result


def screening_requires_blocker(result: ScreeningResult) -> bool:
    """True nếu phác đồ phải bị chặn cho tới khi có xác nhận y khoa."""
    return result.needs_medical_clearance