"""AI WORKOUT PLANNER — Thiết kế lịch tập cá nhân hoá.

Nghiệp vụ:
    - Chọn Workout Split theo số buổi/tuần:
        3 buổi  -> Full Body
        4 buổi  -> Upper / Lower
        5-6 buổi-> Push / Pull / Legs
    - Mỗi buổi gồm: Khởi động & Mobility -> Bài tập chính (Compound trước,
      Isolation sau) -> Cardio/HIIT/LISS -> Giãn cơ Cool-down.
    - Tự động loại bỏ bài tập xung đột với chấn thương của hội viên và
      thay bằng bài tập an toàn tương đương.
    - Điều chỉnh khối lượng (sets/reps/rest) theo mục tiêu và RPE mục tiêu.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


# --------------------------------------------------------------------------
# THƯ VIỆN BÀI TẬP
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Exercise:
    name: str
    target_muscle: str
    pattern: str            # squat | hinge | horizontal_push | vertical_push | ...
    equipment: tuple[str, ...]   # gym | home_dumbbell | calisthenics
    is_compound: bool
    notes: str
    #: Các chấn thương cần tránh bài tập này
    avoid_for: tuple[str, ...] = ()
    #: Bài thay thế an toàn (tên bài)
    alternative: Optional[str] = None


EXERCISE_LIBRARY: list[Exercise] = [
    # ------------------------- NGỰC (CHEST) -------------------------
    Exercise(
        "Barbell Bench Press (Đẩy tạ đòn ghế phẳng)", "Ngực giữa, Vai trước, Tay sau",
        "horizontal_push", ("gym",), True,
        "Ép bả vai sát ghế, hạ tạ chạm ngực dưới kiểm soát 2 giây, không nảy ngực.",
        avoid_for=("shoulder",), alternative="Landmine Press (Đẩy tạ một bên)",
    ),
    Exercise(
        "Incline Dumbbell Press (Đẩy tạ đơn ghế dốc lên)", "Ngực trên, Vai trước, Tay sau",
        "horizontal_push", ("gym", "home_dumbbell"), True,
        "Ghế dốc 30 độ, hạ tạ có kiểm soát 2 giây, ép bả vai sát ghế.",
        avoid_for=("shoulder",), alternative="Landmine Press (Đẩy tạ một bên)",
    ),
    Exercise(
        "Dumbbell Flat Press (Đẩy tạ đơn ghế phẳng)", "Ngực giữa, Vai trước, Tay sau",
        "horizontal_push", ("gym", "home_dumbbell"), True,
        "Cùi chỏ tạo góc 45 độ so với thân, không xoè vai ra sau quá mức.",
        avoid_for=("shoulder",), alternative="Push-up (Chống đẩy)",
    ),
    Exercise(
        "Push-up (Chống đẩy)", "Ngực, Vai trước, Tay sau, Core",
        "horizontal_push", ("gym", "home_dumbbell", "calisthenics"), True,
        "Thân người thẳng một đường, siết core, hạ ngực gần sàn.",
        avoid_for=("wrist",), alternative="Dumbbell Flat Press (Đẩy tạ đơn ghế phẳng)",
    ),
    Exercise(
        "Cable Chest Fly (Ép cáp ngực)", "Ngực trong, Vai trước",
        "isolation", ("gym",), False,
        "Cùi chỏ hơi cong cố định, ép và giữ 1 giây ở điểm co tối đa.",
        avoid_for=("shoulder",), alternative="Pec Deck (Ép ngực máy)",
    ),
    Exercise(
        "Dumbbell Fly (Ép tạ đơn ngực)", "Ngực trong, Vai trước",
        "isolation", ("gym", "home_dumbbell"), False,
        "Chỉ hạ tạ tới ngang vai, không để cùi chỏ xuống dưới thân.",
        avoid_for=("shoulder",), alternative="Ép dây kháng lực (Band Fly)",
    ),

    # ------------------------- LƯNG (BACK) -------------------------
    Exercise(
        "Lat Pulldown (Kéo cáp xô rộng tay)", "Cơ xô (Lats), Tay trước, Lưng giữa",
        "vertical_pull", ("gym",), True,
        "Kéo thanh đòn về phía ngực trên, cảm nhận cùi chỏ đi xuống, không ngửa người quá 15 độ.",
    ),
    Exercise(
        "Barbell Bent-over Row (Kéo tạ đòn cúi người)", "Lưng giữa, Cơ xô, Tay trước",
        "horizontal_pull", ("gym",), True,
        "Giữ lưng trung lập, gập hông 45-60 độ, kéo tạ về rốn.",
        avoid_for=("lower_back",), alternative="Chest-supported Row (Kéo tạ có đệm ngực)",
    ),
    Exercise(
        "Seated Cable Row (Kéo cáp ngồi)", "Lưng giữa, Cơ xô, Tay trước",
        "horizontal_pull", ("gym",), True,
        "Giữ thân người cố định, siết bả vai về sau 1 giây ở điểm co.",
    ),
    Exercise(
        "One-arm Dumbbell Row (Kéo tạ đơn một tay)", "Cơ xô, Lưng giữa, Tay trước",
        "horizontal_pull", ("gym", "home_dumbbell"), True,
        "Tựa tay lên ghế, kéo tạ theo hướng chếch xuống hông, không xoay người.",
    ),
    Exercise(
        "Pull-up / Chin-up (Hít xà)", "Cơ xô, Lưng giữa, Tay trước",
        "vertical_pull", ("gym", "calisthenics"), True,
        "Siết core và mông, kéo ngực lên tới xà hoặc dùng dây hỗ trợ nếu chưa đủ sức.",
        avoid_for=("shoulder",), alternative="Seated Cable Row (Kéo cáp ngồi)",
    ),
    Exercise(
        "Face Pull (Kéo cáp ngang mặt)", "Vai sau, Lưng trên, Xoay ngoài vai",
        "isolation", ("gym",), False,
        "Kéo dây về phía trán, xoay ngoài vai ở cuối chuyển động — bắt buộc cho người tập nhiều.",
    ),
    Exercise(
        "Straight-arm Pulldown (Kéo cáp thẳng tay)", "Cơ xô, Tay sau",
        "isolation", ("gym",), False,
        "Giữ tay gần như thẳng, chỉ duỗi vai — cảm nhận cơ xô căng tối đa.",
    ),

    # ------------------------- CHÂN (LEGS) -------------------------
    Exercise(
        "Barbell Back Squat (Squat tạ đòn)", "Đùi trước, Mông, Đùi sau",
        "squat", ("gym",), True,
        "Hạ xuống tới khi đùi song song sàn hoặc sâu hơn nếu linh hoạt, gối đi theo hướng mũi chân.",
        avoid_for=("knee", "lower_back"), alternative="Box Squat (Squat lên ghế thấp)",
    ),
    Exercise(
        "Goblet Squat (Squat tạ đơn trước ngực)", "Đùi trước, Mông, Core",
        "squat", ("gym", "home_dumbbell", "calisthenics"), True,
        "Giữ tạ sát ngực, ngồi thẳng xuống, gót chân bám sàn.",
        avoid_for=("knee",), alternative="Box Squat (Squat lên ghế thấp)",
    ),
    Exercise(
        "Leg Press (Đạp đùi máy)", "Đùi trước, Mông, Đùi sau",
        "squat", ("gym",), True,
        "Không khoá khớp gối ở đỉnh, không hạ quá sâu làm mông nhấc khỏi đệm.",
    ),
    Exercise(
        "Romanian Deadlift (Deadlift Rumani tạ đòn)", "Đùi sau, Mông, Lưng dưới",
        "hinge", ("gym",), True,
        "Đẩy hông ra sau, hạ tạ dọc theo đùi, cảm nhận căng đùi sau; lưng luôn trung lập.",
        avoid_for=("lower_back",), alternative="Lying Leg Curl (Nằm cuộn đùi sau)",
    ),
    Exercise(
        "Dumbbell Romanian Deadlift (RDL tạ đơn)", "Đùi sau, Mông",
        "hinge", ("gym", "home_dumbbell"), True,
        "Hạ tạ dọc hai bên chân, giữ vai về sau, dừng khi thấy căng đùi sau.",
        avoid_for=("lower_back",), alternative="Glute Bridge (Cầu mông)",
    ),
    Exercise(
        "Hip Thrust (Đẩy hông tạ đòn)", "Mông, Đùi sau",
        "hinge", ("gym", "home_dumbbell"), True,
        "Tựa vai lên ghế, siết mông 1 giây ở đỉnh, không ưỡn lưng dưới.",
    ),
    Exercise(
        "Walking Lunge (Chùng chân bước tới)", "Đùi trước, Mông, Thăng bằng",
        "lunge", ("gym", "home_dumbbell", "calisthenics"), True,
        "Bước đủ dài, gối sau gần sàn, thân người thẳng đứng.",
        avoid_for=("knee",), alternative="Split Squat tại chỗ (Bulgarian Split Squat)",
    ),
    Exercise(
        "Leg Extension (Duỗi đùi máy)", "Đùi trước",
        "isolation", ("gym",), False,
        "Co cơ 1 giây ở đỉnh, hạ chậm 3 giây — an toàn cho khớp gối khi dùng tải nhẹ.",
    ),
    Exercise(
        "Lying Leg Curl (Nằm cuộn đùi sau)", "Đùi sau",
        "isolation", ("gym",), False,
        "Không nhấc hông khỏi đệm, hạ chậm có kiểm soát.",
    ),
    Exercise(
        "Standing Calf Raise (Nhón bắp chân)", "Bắp chân",
        "isolation", ("gym", "home_dumbbell", "calisthenics"), False,
        "Biên độ đầy đủ: xuống hết cỡ và nhón lên cao nhất, giữ 1 giây.",
    ),

    # ------------------------- VAI (SHOULDERS) -------------------------
    Exercise(
        "Seated Dumbbell Shoulder Press (Đẩy vai tạ đơn ngồi)", "Vai trước, Vai giữa, Tay sau",
        "vertical_push", ("gym", "home_dumbbell"), True,
        "Không ưỡn lưng dưới, đẩy tạ theo đường hơi chếch ra trước.",
        avoid_for=("shoulder",), alternative="Landmine Press (Đẩy tạ một bên)",
    ),
    Exercise(
        "Dumbbell Lateral Raise (Nâng vai ngang tạ đơn)", "Vai giữa",
        "isolation", ("gym", "home_dumbbell"), False,
        "Nâng tới ngang vai, hơi nghiêng người về trước, không dùng đà.",
    ),
    Exercise(
        "Cable Lateral Raise (Nâng vai cáp)", "Vai giữa",
        "isolation", ("gym",), False,
        "Lực căng đều suốt biên độ, nâng chậm và hạ chậm.",
    ),
    Exercise(
        "Reverse Pec Deck (Ép vai sau máy)", "Vai sau, Lưng trên",
        "isolation", ("gym",), False,
        "Giữ cùi chỏ hơi cong, siết vai sau 1 giây — cân bằng cho người tập nhiều đẩy ngực.",
    ),

    # ------------------------- TAY (ARMS) -------------------------
    Exercise(
        "Cable Triceps Pushdown (Kéo tay sau cáp)", "Tay sau (Triceps)",
        "isolation", ("gym",), False,
        "Cùi chỏ cố định sát thân, duỗi hết biên độ và siết 1 giây.",
    ),
    Exercise(
        "Overhead Dumbbell Triceps Extension (Duỗi tay sau qua đầu)", "Tay sau (Triceps)",
        "isolation", ("gym", "home_dumbbell"), False,
        "Giữ cùi chỏ hướng lên, không xoè ra hai bên.",
        avoid_for=("shoulder",), alternative="Cable Triceps Pushdown (Kéo tay sau cáp)",
    ),
    Exercise(
        "Barbell Biceps Curl (Cuốn tay trước tạ đòn)", "Tay trước (Biceps)",
        "isolation", ("gym", "home_dumbbell"), False,
        "Cùi chỏ sát thân, không vung người lấy đà.",
    ),
    Exercise(
        "Incline Dumbbell Curl (Cuốn tay trước ghế dốc)", "Tay trước (Biceps)",
        "isolation", ("gym", "home_dumbbell"), False,
        "Ghế dốc 45-60 độ giúp căng tối đa đầu dài cơ nhị đầu.",
    ),
    Exercise(
        "Hammer Curl (Cuốn tạ đơn trung lập)", "Tay trước, Cẳng tay",
        "isolation", ("gym", "home_dumbbell"), False,
        "Giữ cổ tay trung lập, cuốn chậm và siết ở đỉnh.",
    ),

    # ------------------------- CORE & THÂN DƯỚI -------------------------
    Exercise(
        "Plank (Chống sấp giữ thăng bằng)", "Core, Vai, Mông",
        "core", ("gym", "home_dumbbell", "calisthenics"), False,
        "Siết mông và bụng, thân người thẳng, không võng lưng dưới.",
    ),
    Exercise(
        "Hanging Leg Raise (Treo xà nâng chân)", "Bụng dưới, Gập hông",
        "core", ("gym", "calisthenics"), False,
        "Không đung đưa người, nâng chân chậm và hạ chậm.",
        avoid_for=("lower_back",), alternative="Dead Bug (Bọ chết - chống bù trừ core)",
    ),
    Exercise(
        "Cable Crunch (Gập bụng cáp)", "Bụng trên",
        "core", ("gym",), False,
        "Gập cột sống bằng cơ bụng, không kéo bằng tay.",
    ),
    Exercise(
        "Dead Bug (Bọ chết - chống bù trừ core)", "Core sâu, Ổn định cột sống",
        "core", ("gym", "home_dumbbell", "calisthenics"), False,
        "Giữ lưng dưới áp sàn suốt chuyển động — bài tập an toàn nhất cho người đau lưng.",
    ),
    Exercise(
        "Bird Dog (Chim chó - ổn định lưng)", "Core sâu, Lưng dưới, Mông",
        "core", ("gym", "home_dumbbell", "calisthenics"), False,
        "Duỗi chéo tay-chân, giữ hông cân bằng, không xoay người.",
    ),
    Exercise(
        "Back Extension (Duỗi lưng ghế)", "Lưng dưới, Mông, Đùi sau",
        "core", ("gym",), False,
        "Nâng tới khi thân người thẳng, không ưỡn quá mức.",
    ),

    # --------- BÀI THAY THẾ AN TOÀN (dùng khi chấn thương / thiếu thiết bị) ---------
    Exercise(
        "Landmine Press (Đẩy tạ một bên)", "Ngực trên, Vai trước, Tay sau",
        "horizontal_push", ("gym",), True,
        "Bài thay thế an toàn cho vai: đường đẩy chếch lên giúp giảm áp lực lên khớp vai, "
        "rất phù hợp khi vai còn yếu hoặc đang hồi phục.",
    ),
    Exercise(
        "Pec Deck (Ép ngực máy)", "Ngực trong, Vai trước",
        "isolation", ("gym",), False,
        "Quỹ đạo chuyển động cố định giúp kiểm soát tốt, ít áp lực lên khớp vai.",
    ),
    Exercise(
        "Ép dây kháng lực (Band Fly)", "Ngực trong, Vai trước",
        "isolation", ("gym", "home_dumbbell", "calisthenics"), False,
        "Lực căng tăng dần về cuối biên độ, rất nhẹ nhàng cho khớp vai.",
    ),
    Exercise(
        "Push-up tay rộng (Wide Push-up)", "Ngực ngoài, Vai trước",
        "horizontal_push", ("gym", "home_dumbbell", "calisthenics"), True,
        "Đặt tay rộng hơn vai một chút, hạ ngực gần sàn, siết core suốt chuyển động.",
    ),
    Exercise(
        "Chest-supported Row (Kéo tạ có đệm ngực)", "Lưng giữa, Cơ xô, Tay trước",
        "horizontal_pull", ("gym",), True,
        "Ngực tựa đệm giúp cố định thân người, loại bỏ hoàn toàn tải lên lưng dưới.",
    ),
    Exercise(
        "Seated Machine Row (Kéo máy ngồi)", "Lưng giữa, Cơ xô, Tay trước",
        "horizontal_pull", ("gym",), True,
        "Ngực tựa đệm, kéo cùi chỏ về sau và siết bả vai 1 giây.",
    ),
    Exercise(
        "Box Squat (Squat lên ghế thấp)", "Đùi trước, Mông",
        "squat", ("gym", "home_dumbbell"), True,
        "Ngồi chạm nhẹ lên ghế rồi đứng lên — kiểm soát độ sâu, giảm tải lên khớp gối.",
    ),
    Exercise(
        "Split Squat tại chỗ (Bulgarian Split Squat)", "Đùi trước, Mông, Thăng bằng",
        "lunge", ("gym", "home_dumbbell", "calisthenics"), True,
        "Biên độ ngắn hơn Walking Lunge, chân trước chịu lực chính, thân người thẳng.",
    ),
    Exercise(
        "Glute Bridge (Cầu mông)", "Mông, Đùi sau",
        "hinge", ("gym", "home_dumbbell", "calisthenics"), True,
        "Siết mông 1-2 giây ở đỉnh, không ưỡn lưng dưới, rất an toàn cho lưng và gối.",
    ),
    Exercise(
        "Lying Leg Raise (Nâng chân nằm)", "Bụng dưới, Gập hông",
        "core", ("gym", "home_dumbbell", "calisthenics"), False,
        "Giữ lưng dưới áp sàn suốt chuyển động, hạ chân chậm và có kiểm soát.",
    ),
    Exercise(
        "Skull Crusher (Duỗi tay sau nằm ghế)", "Tay sau (Triceps)",
        "isolation", ("gym", "home_dumbbell"), False,
        "Giữ cùi chỏ hướng lên và cố định, hạ tạ về phía trán rồi duỗi ra.",
        avoid_for=("shoulder",), alternative="Cable Triceps Pushdown (Kéo tay sau cáp)",
    ),
]

EXERCISE_BY_NAME: dict[str, Exercise] = {e.name: e for e in EXERCISE_LIBRARY}


#: Ánh xạ mã chống chỉ định PAR-Q -> tên bài tập bị CẤM TUYỆT ĐỐI.
#: AI Workout Planner đọc danh sách này để loại bài trước cả khi xét chấn thương
#: theo vùng, đảm bảo tuân thủ các "hard rules" an toàn y tế.
CONTRAINDICATION_BLOCKS: dict[str, tuple[str, ...]] = {
    "no_axial_load": (
        "Barbell Back Squat (Squat tạ đòn)",
        "Romanian Deadlift (Deadlift Rumani tạ đòn)",
        "Seated Dumbbell Shoulder Press (Đẩy vai tạ đơn ngồi)",
        "Barbell Bent-over Row (Kéo tạ đòn cúi người)",
        "Standing Calf Raise (Nhón bắp chân)",
        "Walking Lunge (Chùng chân bước tới)",
    ),
    "no_spinal_flexion_load": (
        "Cable Crunch (Gập bụng cáp)",
        "Hanging Leg Raise (Treo xà nâng chân)",
        "Back Extension (Duỗi lưng ghế)",
    ),
    "no_high_impact": (
        "Push-up (Chống đẩy)",
    ),
    "no_deep_knee_flexion": (
        "Barbell Back Squat (Squat tạ đòn)",
        "Walking Lunge (Chùng chân bước tới)",
        "Leg Press (Đạp đùi máy)",
        "Split Squat tại chỗ (Bulgarian Split Squat)",
    ),
    "no_overhead_press": (
        "Seated Dumbbell Shoulder Press (Đẩy vai tạ đơn ngồi)",
        "Pull-up / Chin-up (Hít xà)",
        "Overhead Dumbbell Triceps Extension (Duỗi tay sau qua đầu)",
    ),
    "no_shoulder_extension_load": (
        "Barbell Bench Press (Đẩy tạ đòn ghế phẳng)",
        "Dumbbell Fly (Ép tạ đơn ngực)",
        "Cable Chest Fly (Ép cáp ngực)",
    ),
}

#: Bài tập thay thế AN TOÀN cho từng mã chống chỉ định (ưu tiên tuyệt đối)
CONTRAINDICATION_SAFE_ALTERNATIVES: dict[str, tuple[str, ...]] = {
    "no_axial_load": (
        "Leg Press (Đạp đùi máy)",
        "Goblet Squat (Squat tạ đơn trước ngực)",
        "Hip Thrust (Đẩy hông tạ đòn)",
        "Dumbbell Romanian Deadlift (RDL tạ đơn)",
        "Glute Bridge (Cầu mông)",
        "Dead Bug (Bọ chết - chống bù trừ core)",
        "Bird Dog (Chim chó - ổn định lưng)",
    ),
    "no_spinal_flexion_load": (
        "Plank (Chống sấp giữ thăng bằng)",
        "Dead Bug (Bọ chết - chống bù trừ core)",
    ),
    "no_high_impact": (
        "Goblet Squat (Squat tạ đơn trước ngực)",
        "Leg Press (Đạp đùi máy)",
        "Glute Bridge (Cầu mông)",
    ),
    "no_deep_knee_flexion": (
        "Box Squat (Squat lên ghế thấp)",
        "Glute Bridge (Cầu mông)",
        "Lying Leg Curl (Nằm cuộn đùi sau)",
        "Leg Extension (Duỗi đùi máy)",
    ),
    "no_overhead_press": (
        "Landmine Press (Đẩy tạ một bên)",
        "Dumbbell Lateral Raise (Nâng vai ngang tạ đơn)",
        "Cable Lateral Raise (Nâng vai cáp)",
        "Reverse Pec Deck (Ép vai sau máy)",
    ),
    "no_shoulder_extension_load": (
        "Pec Deck (Ép ngực máy)",
        "Landmine Press (Đẩy tạ một bên)",
        "Ép dây kháng lực (Band Fly)",
    ),
}


def _contraindication_replacement(
    blocked_name: str, contraindications: list[str], injuries: list[str]
) -> Optional[str]:
    """Tìm bài thay thế an toàn cho một bài bị cấm bởi chống chỉ định."""
    candidates: list[str] = []
    for code in contraindications:
        candidates.extend(CONTRAINDICATION_SAFE_ALTERNATIVES.get(code, ()))

    for name in candidates:
        ex = EXERCISE_BY_NAME.get(name)
        if ex is None or ex.name == blocked_name:
            continue
        # Không chọn bài cũng bị cấm hoặc xung đột chấn thương
        if any(code in CONTRAINDICATION_BLOCKS
               and ex.name in CONTRAINDICATION_BLOCKS[code]
               for code in contraindications):
            continue
        if any(inj in ex.avoid_for for inj in injuries):
            continue
        return ex.name
    return None


# --------------------------------------------------------------------------
# WORKOUT SPLITS
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class SessionTemplate:
    day_label: str
    focus: str
    warmup: str
    cooldown: str
    #: (tên bài tập, sets, reps, rest_seconds)
    blocks: tuple[tuple[str, int, str, int], ...]


SPLIT_TEMPLATES: dict[str, dict] = {
    # ---------------------- 3 BUỔI / TUẦN: FULL BODY ----------------------
    "full_body_3": {
        "split_name": "Full Body (Toàn thân) — 3 buổi/tuần",
        "description": (
            "Tần suất 3 buổi/tuần là lựa chọn tối ưu cho người mới hoặc người bận rộn: "
            "mỗi nhóm cơ được kích thích 3 lần/tuần, đủ để tăng cơ và tăng sức mạnh "
            "trong khi vẫn có 4 ngày nghỉ để phục hồi."
        ),
        "sessions": [
            SessionTemplate(
                "Thứ 2", "Full Body A (Toàn thân — Ưu tiên Đẩy & Chân)",
                "5 phút xe đạp/đi bộ nhanh + Xoay khớp vai-hông + 10 lần Squat không tải + Cat-Cow 8 lần",
                "Giãn cơ tĩnh 5 phút: ngực, đùi trước, đùi sau, lưng xô",
                (
                    ("Barbell Back Squat (Squat tạ đòn)", 4, "8-10", 120),
                    ("Incline Dumbbell Press (Đẩy tạ đơn ghế dốc lên)", 4, "8-10", 90),
                    ("Lat Pulldown (Kéo cáp xô rộng tay)", 4, "10-12", 90),
                    ("Seated Dumbbell Shoulder Press (Đẩy vai tạ đơn ngồi)", 3, "10-12", 75),
                    ("Plank (Chống sấp giữ thăng bằng)", 3, "40-60 giây", 60),
                ),
            ),
            SessionTemplate(
                "Thứ 4", "Full Body B (Toàn thân — Ưu tiên Kéo & Đùi sau)",
                "5 phút đi bộ dốc + Xoay khớp + Glute Bridge 15 lần + Dead Bug 10 lần",
                "Giãn cơ tĩnh 5 phút: đùi sau, mông, lưng, vai sau",
                (
                    ("Romanian Deadlift (Deadlift Rumani tạ đòn)", 4, "8-10", 120),
                    ("Seated Cable Row (Kéo cáp ngồi)", 4, "10-12", 90),
                    ("Dumbbell Flat Press (Đẩy tạ đơn ghế phẳng)", 4, "8-10", 90),
                    ("Walking Lunge (Chùng chân bước tới)", 3, "10-12 mỗi chân", 90),
                    ("Face Pull (Kéo cáp ngang mặt)", 3, "15", 60),
                ),
            ),
            SessionTemplate(
                "Thứ 6", "Full Body C (Toàn thân — Ưu tiên Vai & Tay)",
                "5 phút xe đạp + Xoay khớp + Ép dây kháng lực kích hoạt vai 15 lần",
                "Giãn cơ tĩnh 5 phút: vai, tay trước, tay sau, ngực",
                (
                    ("Goblet Squat (Squat tạ đơn trước ngực)", 4, "10-12", 90),
                    ("Push-up (Chống đẩy)", 4, "12-15", 75),
                    ("One-arm Dumbbell Row (Kéo tạ đơn một tay)", 4, "10-12 mỗi tay", 75),
                    ("Dumbbell Lateral Raise (Nâng vai ngang tạ đơn)", 4, "12-15", 60),
                    ("Barbell Biceps Curl (Cuốn tay trước tạ đòn)", 3, "10-12", 60),
                    ("Cable Triceps Pushdown (Kéo tay sau cáp)", 3, "12-15", 60),
                ),
            ),
        ],
    },

    # -------------------- 4 BUỔI / TUẦN: UPPER / LOWER --------------------
    "upper_lower_4": {
        "split_name": "Upper / Lower Split — 4 buổi/tuần",
        "description": (
            "Chia thân trên và thân dưới, mỗi vùng tập 2 lần/tuần. Đây là split "
            "cân bằng nhất giữa hiệu quả tăng cơ và khả năng phục hồi, phù hợp "
            "với hầu hết hội viên đã có 3-6 tháng kinh nghiệm."
        ),
        "sessions": [
            SessionTemplate(
                "Thứ 2", "Upper Body A (Thân trên — Ưu tiên Ngực & Xô)",
                "5 phút đi bộ máy + Xoay khớp vai + Giãn cơ ngực động (Dynamic Stretching) 8 lần mỗi bên",
                "Giãn cơ tĩnh 5 phút: ngực, xô, vai trước",
                (
                    ("Incline Dumbbell Press (Đẩy tạ đơn ghế dốc lên)", 4, "8-10", 90),
                    ("Lat Pulldown (Kéo cáp xô rộng tay)", 4, "10-12", 90),
                    ("Seated Dumbbell Shoulder Press (Đẩy vai tạ đơn ngồi)", 3, "10-12", 75),
                    ("Seated Cable Row (Kéo cáp ngồi)", 3, "10-12", 75),
                    ("Dumbbell Lateral Raise (Nâng vai ngang tạ đơn)", 4, "12-15", 60),
                    ("Cable Triceps Pushdown (Kéo tay sau cáp)", 3, "12-15", 60),
                ),
            ),
            SessionTemplate(
                "Thứ 3", "Lower Body A (Thân dưới — Ưu tiên Đùi trước & Mông)",
                "5 phút xe đạp + Xoay khớp hông-gối + Glute Bridge 15 lần + Squat không tải 10 lần",
                "Giãn cơ tĩnh 5 phút: đùi trước, mông, bắp chân",
                (
                    ("Barbell Back Squat (Squat tạ đòn)", 4, "8-10", 120),
                    ("Romanian Deadlift (Deadlift Rumani tạ đòn)", 4, "8-10", 120),
                    ("Leg Press (Đạp đùi máy)", 3, "12-15", 90),
                    ("Lying Leg Curl (Nằm cuộn đùi sau)", 3, "12-15", 60),
                    ("Standing Calf Raise (Nhón bắp chân)", 4, "15-20", 45),
                    ("Plank (Chống sấp giữ thăng bằng)", 3, "45-60 giây", 60),
                ),
            ),
            SessionTemplate(
                "Thứ 5", "Upper Body B (Thân trên — Ưu tiên Xô & Vai)",
                "5 phút đi bộ dốc + Xoay khớp + Face Pull nhẹ 15 lần kích hoạt vai sau",
                "Giãn cơ tĩnh 5 phút: xô, vai sau, tay trước",
                (
                    ("Pull-up / Chin-up (Hít xà)", 4, "6-10", 120),
                    ("Barbell Bench Press (Đẩy tạ đòn ghế phẳng)", 4, "8-10", 120),
                    ("One-arm Dumbbell Row (Kéo tạ đơn một tay)", 4, "10-12 mỗi tay", 75),
                    ("Cable Chest Fly (Ép cáp ngực)", 3, "12-15", 60),
                    ("Reverse Pec Deck (Ép vai sau máy)", 3, "15", 60),
                    ("Incline Dumbbell Curl (Cuốn tay trước ghế dốc)", 3, "10-12", 60),
                ),
            ),
            SessionTemplate(
                "Thứ 6", "Lower Body B (Thân dưới — Ưu tiên Đùi sau & Mông)",
                "5 phút xe đạp + Xoay khớp + Bird Dog 10 lần + Bước hông sang ngang 10 lần",
                "Giãn cơ tĩnh 5 phút: đùi sau, mông, hông",
                (
                    ("Hip Thrust (Đẩy hông tạ đòn)", 4, "10-12", 90),
                    ("Walking Lunge (Chùng chân bước tới)", 3, "12 mỗi chân", 90),
                    ("Leg Extension (Duỗi đùi máy)", 3, "12-15", 60),
                    ("Lying Leg Curl (Nằm cuộn đùi sau)", 3, "12-15", 60),
                    ("Standing Calf Raise (Nhón bắp chân)", 4, "15-20", 45),
                    ("Hanging Leg Raise (Treo xà nâng chân)", 3, "10-12", 60),
                ),
            ),
        ],
    },

    # ------------------ 5-6 BUỔI / TUẦN: PUSH / PULL / LEGS ------------------
    "ppl_6": {
        "split_name": "Push / Pull / Legs — 6 buổi/tuần",
        "description": (
            "Mỗi nhóm cơ được tập 2 lần/tuần với khối lượng chuyên sâu hơn. "
            "Split này đòi hỏi khả năng phục hồi tốt: bắt buộc ngủ đủ 7.5-9 tiếng "
            "và nạp đủ đạm, nếu không sẽ nhanh chóng rơi vào trạng thái quá tải."
        ),
        "sessions": [
            SessionTemplate(
                "Thứ 2", "Push A (Đẩy — Ngực, Vai, Tay sau)",
                "5 phút đi bộ máy + Xoay khớp vai + Ép dây kháng lực 15 lần",
                "Giãn cơ tĩnh 5 phút: ngực, vai trước, tay sau",
                (
                    ("Barbell Bench Press (Đẩy tạ đòn ghế phẳng)", 4, "6-8", 150),
                    ("Seated Dumbbell Shoulder Press (Đẩy vai tạ đơn ngồi)", 4, "8-10", 90),
                    ("Incline Dumbbell Press (Đẩy tạ đơn ghế dốc lên)", 3, "10-12", 90),
                    ("Dumbbell Lateral Raise (Nâng vai ngang tạ đơn)", 4, "12-15", 60),
                    ("Cable Triceps Pushdown (Kéo tay sau cáp)", 4, "10-12", 60),
                ),
            ),
            SessionTemplate(
                "Thứ 3", "Pull A (Kéo — Xô, Lưng giữa, Tay trước)",
                "5 phút đi bộ dốc + Xoay khớp + Dead Hang treo xà 20 giây x2",
                "Giãn cơ tĩnh 5 phút: xô, lưng, tay trước, cẳng tay",
                (
                    ("Pull-up / Chin-up (Hít xà)", 4, "6-10", 120),
                    ("Barbell Bent-over Row (Kéo tạ đòn cúi người)", 4, "8-10", 120),
                    ("Seated Cable Row (Kéo cáp ngồi)", 3, "10-12", 75),
                    ("Face Pull (Kéo cáp ngang mặt)", 3, "15", 60),
                    ("Barbell Biceps Curl (Cuốn tay trước tạ đòn)", 4, "10-12", 60),
                ),
            ),
            SessionTemplate(
                "Thứ 4", "Legs A (Chân — Ưu tiên Đùi trước)",
                "5 phút xe đạp + Xoay khớp hông-gối-cổ chân + Squat không tải 15 lần",
                "Giãn cơ tĩnh 6 phút: đùi trước, đùi sau, mông, bắp chân",
                (
                    ("Barbell Back Squat (Squat tạ đòn)", 5, "6-8", 180),
                    ("Leg Press (Đạp đùi máy)", 4, "10-12", 90),
                    ("Romanian Deadlift (Deadlift Rumani tạ đòn)", 3, "10-12", 90),
                    ("Leg Extension (Duỗi đùi máy)", 3, "12-15", 60),
                    ("Standing Calf Raise (Nhón bắp chân)", 5, "12-15", 45),
                ),
            ),
            SessionTemplate(
                "Thứ 5", "Push B (Đẩy — Ưu tiên Vai & Ngực trên)",
                "5 phút đi bộ máy + Xoay khớp vai + Band Pull-apart 20 lần",
                "Giãn cơ tĩnh 5 phút: vai, ngực trên, tay sau",
                (
                    ("Incline Dumbbell Press (Đẩy tạ đơn ghế dốc lên)", 4, "8-10", 90),
                    ("Seated Dumbbell Shoulder Press (Đẩy vai tạ đơn ngồi)", 4, "10-12", 90),
                    ("Cable Chest Fly (Ép cáp ngực)", 3, "12-15", 60),
                    ("Cable Lateral Raise (Nâng vai cáp)", 4, "15", 45),
                    ("Overhead Dumbbell Triceps Extension (Duỗi tay sau qua đầu)", 3, "10-12", 60),
                ),
            ),
            SessionTemplate(
                "Thứ 6", "Pull B (Kéo — Ưu tiên Xô rộng & Lưng dưới)",
                "5 phút đi bộ dốc + Xoay khớp + Cat-Cow 10 lần",
                "Giãn cơ tĩnh 5 phút: xô, lưng dưới, tay trước",
                (
                    ("Lat Pulldown (Kéo cáp xô rộng tay)", 4, "10-12", 90),
                    ("One-arm Dumbbell Row (Kéo tạ đơn một tay)", 4, "10-12 mỗi tay", 75),
                    ("Straight-arm Pulldown (Kéo cáp thẳng tay)", 3, "12-15", 60),
                    ("Reverse Pec Deck (Ép vai sau máy)", 3, "15", 60),
                    ("Hammer Curl (Cuốn tạ đơn trung lập)", 4, "10-12", 60),
                ),
            ),
            SessionTemplate(
                "Thứ 7", "Legs B (Chân — Ưu tiên Đùi sau & Mông) + Core",
                "5 phút xe đạp + Xoay khớp + Glute Bridge 15 lần + Bird Dog 10 lần",
                "Giãn cơ tĩnh 6 phút + Foam Rolling đùi trước & đùi sau 3 phút",
                (
                    ("Hip Thrust (Đẩy hông tạ đòn)", 4, "10-12", 90),
                    ("Romanian Deadlift (Deadlift Rumani tạ đòn)", 4, "10-12", 90),
                    ("Walking Lunge (Chùng chân bước tới)", 3, "12 mỗi chân", 75),
                    ("Lying Leg Curl (Nằm cuộn đùi sau)", 4, "12-15", 60),
                    ("Hanging Leg Raise (Treo xà nâng chân)", 3, "10-15", 60),
                    ("Back Extension (Duỗi lưng ghế)", 3, "15", 45),
                ),
            ),
        ],
    },

    # -------------- 5 BUỔI / TUẦN: PPL + UPPER/LOWER HYBRID --------------
    "ppl_5": {
        "split_name": "Push / Pull / Legs + Upper / Lower — 5 buổi/tuần",
        "description": (
            "Biến thể 5 buổi của Push-Pull-Legs: thêm một buổi Upper để tăng "
            "tần suất cho thân trên mà vẫn giữ đủ ngày nghỉ phục hồi."
        ),
        "sessions": None,  # Sinh tự động từ ppl_6 (bỏ buổi Legs B)
    },
}


# --------------------------------------------------------------------------
# ĐIỀU CHỈNH THEO MỤC TIÊU
# --------------------------------------------------------------------------
GOAL_TRAINING_PARAMS: dict[str, dict] = {
    "cutting": {
        "rep_bias": "Giữ tải nặng ở 6-12 reps để bảo toàn cơ trong thâm hụt calo",
        "rest_bias": "Nghỉ 60-120 giây, rút ngắn ở bài isolation để tăng mật độ tập",
        "target_rpe": "RPE 7-8 (chừa 2-3 reps trong bình)",
        "cardio_type": "LISS + HIIT kết hợp",
        "volume_note": "Duy trì khối lượng tạ nặng, TUYỆT ĐỐI không cắt xuống tạ nhẹ - rep cao "
                       "vì đó là nguyên nhân mất cơ phổ biến nhất khi giảm cân.",
    },
    "bulking": {
        "rep_bias": "Ưu tiên 6-10 reps với tải tăng dần mỗi tuần",
        "rest_bias": "Nghỉ đủ 90-180 giây ở bài compound để đảm bảo chất lượng hiệp",
        "target_rpe": "RPE 8-9 (chừa 1-2 reps trong bình)",
        "cardio_type": "Cardio tối thiểu (chỉ để tim mạch khoẻ)",
        "volume_note": "Tăng dần khối lượng mỗi tuần 2.5-5% (Progressive Overload).",
    },
    "recomp": {
        "rep_bias": "Kết hợp 6-10 reps (compound) và 12-20 reps (isolation)",
        "rest_bias": "Nghỉ 75-120 giây",
        "target_rpe": "RPE 8 (chừa 2 reps)",
        "cardio_type": "LISS nhẹ + 1 buổi HIIT/tuần",
        "volume_note": "Tập trung tăng tải từ từ ở bài compound - đây là động lực tăng cơ chính.",
    },
    "endurance": {
        "rep_bias": "Tải trung bình 12-15 reps, tempo nhanh hơn",
        "rest_bias": "Nghỉ ngắn 45-75 giây để tăng sức bền cơ",
        "target_rpe": "RPE 6-7 (chừa 3-4 reps)",
        "cardio_type": "Cardio Zone 2 chủ đạo + Interval",
        "volume_note": "Ưu tiên khả năng duy trì cường độ trong thời gian dài.",
    },
}


def _cardio_prescription(
    goal: str, body_fat_pct: float, training_days: int, injuries: list[str]
) -> dict:
    """Kê đơn Cardio theo % Body Fat, mục tiêu và chấn thương."""
    knee_issue = "knee" in injuries
    back_issue = "lower_back" in injuries

    if knee_issue or back_issue:
        low_impact = "Ưu tiên bài ít tác động khớp: xe đạp, máy elliptical, bơi hoặc đi bộ dốc."
    else:
        low_impact = "Có thể dùng máy chạy bộ và bài nhảy dây."

    if body_fat_pct >= 25 or goal in ("cutting", "recomp"):
        if goal == "cutting":
            plan = [
                "LISS sau mỗi buổi tập tạ: 15-20 phút đi bộ dốc (Incline 8-12%, tốc độ 4.5-5.5 km/h) ở vùng nhịp tim 60-70% HRmax.",
                "HIIT 2 buổi/tuần (cách ngày tập tạ): 8 hiệp x (30 giây nỗ lực tối đa : 90 giây hồi phục) trên xe đạp hoặc máy chạy.",
                "NEAT mỗi ngày: duy trì 8.000-10.000 bước chân kể cả ngày nghỉ.",
            ]
        else:
            plan = [
                "LISS 20-25 phút đi bộ dốc sau buổi tập tạ, 3-4 buổi/tuần (nhịp tim 60-70% HRmax).",
                "HIIT 1 buổi/tuần: 6 hiệp x (30 giây nỗ lực : 90 giây hồi phục).",
                "NEAT: duy trì 8.000-10.000 bước chân/ngày.",
            ]
    elif body_fat_pct >= 18:
        plan = [
            "LISS 15 phút đi bộ dốc sau mỗi buổi tập tạ (nhịp tim 60-65% HRmax).",
            "HIIT 1-2 buổi/tuần: 8 hiệp x (30 giây nỗ lực : 90 giây hồi phục).",
            "NEAT: duy trì 8.000 bước chân/ngày.",
        ]
    elif body_fat_pct >= 14:
        plan = [
            "LISS 10-12 phút đi bộ dốc sau buổi tập tạ để hỗ trợ phục hồi.",
            "HIIT 1 buổi/tuần nếu muốn siết nét thêm (6-8 hiệp).",
            "NEAT: 7.000-9.000 bước chân/ngày.",
        ]
    else:
        plan = [
            "Cardio nhẹ 10 phút sau tập để phục hồi, không cần cardio đốt mỡ.",
            "HIIT tối đa 1 buổi/tuần để duy trì tim mạch.",
            "NEAT: 7.000 bước chân/ngày là đủ.",
        ]

    return {
        "type": GOAL_TRAINING_PARAMS.get(goal, GOAL_TRAINING_PARAMS["recomp"])["cardio_type"],
        "weekly_sessions": 2 if goal == "cutting" else 1,
        "details": plan,
        "low_impact_note": low_impact,
    }


def _adjust_reps_for_goal(reps: str, goal: str) -> str:
    """Điều chỉnh khoảng reps theo mục tiêu (giữ nguyên compound nặng)."""
    if goal == "endurance":
        return reps.replace("6-8", "12-15").replace("8-10", "12-15").replace("6-10", "12-15")
    if goal == "cutting":
        return reps.replace("15-20", "12-15")
    return reps


def _adjust_sets_for_goal(sets: int, goal: str, is_compound: bool) -> int:
    """Tinh chỉnh số hiệp theo mục tiêu."""
    if goal == "cutting":
        # Giảm nhẹ volume ở bài isolation để tiết kiệm thời gian, giữ compound
        return sets if is_compound else max(2, sets - 1)
    if goal == "bulking":
        return sets + 1 if is_compound else sets
    return sets


def _build_sessions(
    split_key: str,
    training_days: int,
    goal: str,
    injuries: list[str],
    location: str,
    session_minutes: int,
    contraindications: Optional[list[str]] = None,
) -> tuple[list[dict], list[str]]:
    """Sinh danh sách buổi tập đã cá nhân hoá.

    Thứ tự ưu tiên khi lọc bài tập:
      1. Chống chỉ định y tế PAR-Q (hard rules — tuyệt đối không vi phạm)
      2. Chấn thương theo vùng (đau lưng, gối, vai...)
      3. Thiết bị tại nơi tập
      4. Ngân sách thời gian của buổi tập
    """
    contraindications = contraindications or []
    template = SPLIT_TEMPLATES.get(split_key, SPLIT_TEMPLATES["upper_lower_4"])
    raw_sessions = template.get("sessions")

    # 5 buổi/tuần: lấy PPL 6 buổi và bỏ buổi "Legs B"
    if raw_sessions is None:
        raw_sessions = [
            s for s in SPLIT_TEMPLATES["ppl_6"]["sessions"] if "Legs B" not in s.focus
        ]

    raw_sessions = list(raw_sessions)[:training_days]
    goal_params = GOAL_TRAINING_PARAMS.get(goal, GOAL_TRAINING_PARAMS["recomp"])
    substitutions: list[str] = []
    sessions: list[dict] = []

    # Ngân sách thời gian: ước lượng ~2.5 phút/hiệp bao gồm nghỉ
    max_blocks = max(3, int(session_minutes / 8.5))

    for session in raw_sessions:
        exercises: list[dict] = []
        seen_names: set[str] = set()
        for ex_name, sets, reps, rest in session.blocks:
            ex = EXERCISE_BY_NAME.get(ex_name)
            if ex is None:
                continue

            # 0) CHỐNG CHỈ ĐỊNH Y TẾ (PAR-Q) — ưu tiên tuyệt đối
            blocked_by = [
                code for code in contraindications
                if ex.name in CONTRAINDICATION_BLOCKS.get(code, ())
            ]
            if blocked_by:
                alt = _contraindication_replacement(ex.name, contraindications, injuries)
                alt_ex = EXERCISE_BY_NAME.get(alt) if alt else None
                if alt_ex and alt_ex.name not in seen_names:
                    substitutions.append(
                        f"⚠️ '{ex.name}' bị LOẠI do ràng buộc an toàn y tế "
                        f"({', '.join(blocked_by)}). Đã thay bằng '{alt_ex.name}'."
                    )
                    ex = alt_ex
                else:
                    substitutions.append(
                        f"⚠️ Đã loại bỏ '{ex.name}' do ràng buộc an toàn y tế "
                        f"({', '.join(blocked_by)})."
                    )
                    continue

            # 1) Loại bài tập xung đột chấn thương
            if any(inj in ex.avoid_for for inj in injuries):
                alt_name = ex.alternative
                alt_ex = EXERCISE_BY_NAME.get(alt_name) if alt_name else None
                if alt_ex and not any(inj in alt_ex.avoid_for for inj in injuries):
                    substitutions.append(
                        f"'{ex.name}' được thay bằng '{alt_ex.name}' để bảo vệ "
                        f"vùng chấn thương của bạn."
                    )
                    ex = alt_ex
                else:
                    substitutions.append(
                        f"Đã loại bỏ '{ex.name}' do không phù hợp với tình trạng "
                        f"chấn thương hiện tại của bạn."
                    )
                    continue

            # 2) Kiểm tra thiết bị theo nơi tập
            if location not in ex.equipment and location != "gym":
                alt_name = ex.alternative
                alt_ex = EXERCISE_BY_NAME.get(alt_name) if alt_name else None
                if alt_ex and location in alt_ex.equipment:
                    substitutions.append(
                        f"'{ex.name}' được thay bằng '{alt_ex.name}' vì bạn tập tại nhà."
                    )
                    ex = alt_ex
                else:
                    # Tìm bài cùng pattern phù hợp thiết bị
                    same_pattern = [
                        e for e in EXERCISE_LIBRARY
                        if e.pattern == ex.pattern
                        and location in e.equipment
                        and not any(inj in e.avoid_for for inj in injuries)
                    ]
                    if same_pattern:
                        picked = max(same_pattern, key=lambda e: e.is_compound)
                        substitutions.append(
                            f"'{ex.name}' được thay bằng '{picked.name}' cho phù hợp "
                            f"với điều kiện tập luyện của bạn."
                        )
                        ex = picked
                    elif location not in ex.equipment:
                        continue

            sets_adj = _adjust_sets_for_goal(sets, goal, ex.is_compound)

            # Sau khi thay thế, nhiều bài gốc có thể trỏ về cùng một bài an toàn
            # (VD: cả Bench Press và Incline Press đều thay bằng Landmine Press).
            # Bỏ qua bài trùng để buổi tập không bị lặp lại vô nghĩa.
            if ex.name in seen_names:
                continue
            seen_names.add(ex.name)

            exercises.append({
                "name": ex.name,
                "target_muscle": ex.target_muscle,
                "movement": ex.pattern,
                "type": "Compound (Đa khớp)" if ex.is_compound else "Isolation (Đơn khớp)",
                "sets": sets_adj,
                "reps": _adjust_reps_for_goal(reps, goal),
                "rest_seconds": rest,
                "rpe": goal_params["target_rpe"],
                "notes": ex.notes,
            })

        # Cắt bớt nếu vượt ngân sách thời gian: giữ compound, bỏ isolation cuối
        if len(exercises) > max_blocks:
            compounds = [e for e in exercises if "Compound" in e["type"]]
            isolations = [e for e in exercises if "Isolation" in e["type"]]
            keep = compounds[:max_blocks]
            keep += isolations[: max(0, max_blocks - len(keep))]
            exercises = keep

        if not exercises:
            continue

        sessions.append({
            "day": session.day_label,
            "focus": session.focus,
            "warmup": session.warmup,
            "exercises": exercises,
            "cooldown": session.cooldown,
            "estimated_minutes": sum(
                e["sets"] * (1.0 + e["rest_seconds"] / 60.0) for e in exercises
            ).__round__(0),
        })

    return sessions, substitutions


def build_workout_plan(
    goal: str,
    activity_level: str,
    training_days_per_week: int,
    session_minutes: int,
    training_location: str,
    body_fat_pct: float,
    gender: str,
    injuries: Optional[list[str]] = None,
    age: Optional[int] = None,
    contraindications: Optional[list[str]] = None,
    pregnancy_modified: bool = False,
) -> dict:
    """Sinh lịch tập hoàn chỉnh theo nghiệp vụ AI Workout Planner.

    `contraindications` là danh sách mã cấm từ sàng lọc PAR-Q — được áp dụng
    TRƯỚC chấn thương theo vùng vì đây là ràng buộc an toàn y tế.
    """
    injuries = injuries or []
    contraindications = contraindications or []

    # --- Bước 1: chọn split theo số buổi/tuần ---
    days = max(2, min(6, training_days_per_week))
    if days <= 3:
        split_key = "full_body_3"
        days = 3
    elif days == 4:
        split_key = "upper_lower_4"
    elif days == 5:
        split_key = "ppl_5"
    else:
        split_key = "ppl_6"
        days = 6

    template = SPLIT_TEMPLATES[split_key]
    sessions, substitutions = _build_sessions(
        split_key, days, goal, injuries, training_location, session_minutes,
        contraindications=contraindications,
    )

    # --- Bước 2: điều chỉnh cho người lớn tuổi / người mới / thai kỳ ---
    extra_notes: list[str] = []
    if age and age >= 50:
        extra_notes.append(
            "Trên 50 tuổi: tăng thời gian khởi động lên 10-12 phút, thêm 2 hiệp "
            "bài tập thăng bằng (Single-leg Stand, Bird Dog) vào cuối mỗi buổi."
        )
    if pregnancy_modified:
        extra_notes.append(
            "🤰 Chương trình điều chỉnh cho THAI KỲ: không nằm ngửa sau tam cá nguyệt "
            "thứ nhất, không nén bụng, không nín thở rặn (Valsalva), giữ nhịp tim ở mức "
            "có thể trò chuyện được. Ưu tiên bài tập sàn chậu và ổn định core. "
            "Tuyệt đối tránh bài tập có nguy cơ té ngã."
        )
    if days >= 5:
        extra_notes.append(
            "Với 5-6 buổi/tuần, dấu hiệu quá tải là điều tối cần lưu ý: nếu nhịp tim "
            "nghỉ tăng trên 5 bpm so với bình thường, chất lượng giấc ngủ giảm hoặc "
            "sức mạnh tụt liên tục 2 buổi liên tiếp — hãy giảm 1 buổi và tăng nghỉ ngơi."
        )

    # Cảnh báo tổng hợp về chống chỉ định đã áp dụng
    contraindication_notes: list[str] = []
    if "no_axial_load" in contraindications:
        contraindication_notes.append(
            "Đã loại toàn bộ bài nén trục dọc cột sống nặng (Barbell Back Squat, "
            "Conventional Deadlift) và thay bằng Belt Squat / Leg Press / Goblet Squat / "
            "Hip Thrust."
        )
    if "no_high_impact" in contraindications:
        contraindication_notes.append(
            "Đã loại toàn bộ bài cardio chấn động (chạy tốc độ cao, nhảy dây, HIIT nhảy) "
            "và chuyển sang cardio không chấn động (đi bộ dốc, đạp xe tĩnh, bơi, elliptical)."
        )
    if "no_overhead_press" in contraindications:
        contraindication_notes.append(
            "Đã loại các bài đẩy tạ qua đầu và thay bằng Landmine Press / đẩy tạ đơn "
            "tư thế trung lập."
        )
    if "no_deep_knee_flexion" in contraindications:
        contraindication_notes.append(
            "Đã giới hạn biên độ gập gối — dùng Box Squat, Glute Bridge, Leg Curl "
            "thay cho Squat sâu và Walking Lunge."
        )

    cardio = _cardio_prescription(goal, body_fat_pct, days, injuries)
    # Ghi đè cardio nếu có chống chỉ định chấn động
    if "no_high_impact" in contraindications:
        cardio = {
            **cardio,
            "type": "Cardio KHÔNG CHẤN ĐỘNG (LISS) — bắt buộc do ràng buộc y tế",
            "low_impact_note": (
                "⛔ Do tình trạng sức khỏe của bạn, TUYỆT ĐỐI không chạy bộ tốc độ cao, "
                "không nhảy dây và không tập HIIT nhảy. Chỉ dùng: đi bộ dốc trên máy, "
                "đạp xe tĩnh, bơi lội, máy elliptical, chèo thuyền."
            ),
            "details": [
                d.replace("HIIT", "LISS thay thế HIIT (do ràng buộc y tế)")
                for d in cardio["details"]
            ] + [
                "⛔ Đã loại bỏ mọi bài cardio chấn động theo ràng buộc an toàn y tế.",
            ],
        }
    goal_params = GOAL_TRAINING_PARAMS.get(goal, GOAL_TRAINING_PARAMS["recomp"])

    return {
        "split_type": template["split_name"],
        "split_rationale": template["description"],
        "training_days_per_week": days,
        "session_minutes": session_minutes,
        "training_location": training_location,
        "progression_rule": (
            "Nguyên tắc tăng tiến (Progressive Overload): khi bạn hoàn thành được "
            "số reps tối đa của khoảng reps ở TẤT CẢ các hiệp với kỹ thuật tốt, "
            "hãy tăng tạ thêm 2.5kg (bài thân trên) hoặc 5kg (bài thân dưới) "
            "ở buổi tập kế tiếp. Ghi lại mức tạ mỗi buổi vào Nhật ký tập luyện."
        ),
        "rep_guidance": goal_params["rep_bias"],
        "rest_guidance": goal_params["rest_bias"],
        "target_rpe": goal_params["target_rpe"],
        "volume_note": goal_params["volume_note"],
        "sessions": sessions,
        "cardio": cardio,
        "exercise_substitutions": substitutions,
        "extra_notes": extra_notes,
        "medical_safety": {
            "contraindications_applied": contraindications,
            "notes": contraindication_notes,
            "pregnancy_modified": pregnancy_modified,
            "disclaimer": (
                "Các ràng buộc an toàn y tế ở trên được áp dụng tự động dựa trên bảng "
                "sàng lọc PAR-Q+ của bạn. Nếu tình trạng sức khỏe thay đổi, hãy cập nhật "
                "lại phiếu sàng lọc để AI điều chỉnh phác đồ."
                if contraindications or pregnancy_modified else None
            ),
        },
        "weekly_structure": (
            "Lịch chuẩn: tập các buổi cách nhau, chèn ngày nghỉ hoặc nghỉ chủ động "
            "giữa các buổi liên tiếp. Không tập 2 buổi cùng một nhóm cơ lớn "
            "liên tiếp trong vòng 48 giờ."
        ),
    }


def serialize_workout_plan(plan: dict) -> dict:
    """Chuyển plan thành dict JSON-safe."""
    return asdict(plan) if hasattr(plan, "__dataclass_fields__") else plan