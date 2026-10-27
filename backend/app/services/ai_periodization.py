"""PERIODIZATION ENGINE — Chu kỳ hóa, tăng tiến mức tạ & đổi bài tập tức thì.

Nghiệp vụ:
    1. Ước tính 1RM: Epley  `1RM = Weight x (1 + Reps/30)`
    2. Progressive Overload tự động: hoàn thành đủ reps ở cận trên với RPE < 8
       -> tuần sau tăng 2.5kg (thân trên) / 5kg (thân dưới)
    3. Deload Week: sau 6-8 tuần tập nặng liên tục -> giảm 40% volume hoặc 10-20% tạ
    4. Smart Exercise Swap: đổi bài tức thì khi máy hỏng / có người dùng / đau khớp
    5. Bảng %1RM theo mục tiêu (sức mạnh / tăng cơ / sức bền)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.services.ai_workout import EXERCISE_BY_NAME, EXERCISE_LIBRARY, Exercise


# --------------------------------------------------------------------------
# 1RM & BẢNG TẢI TRỌNG
# --------------------------------------------------------------------------
def estimate_1rm(weight_kg: float, reps: int) -> float:
    """Ước tính 1RM theo công thức Epley: 1RM = W x (1 + Reps/30).

    Chỉ chính xác nhất trong khoảng 1-12 reps. Trên 12 reps sai số tăng nhanh.
    """
    if reps <= 0 or weight_kg <= 0:
        return 0.0
    if reps == 1:
        return round(weight_kg, 1)
    return round(weight_kg * (1 + reps / 30.0), 1)


def estimate_1rm_brzycki(weight_kg: float, reps: int) -> float:
    """Ước tính 1RM theo công thức Brzycki (chính xác hơn ở 2-6 reps).

    1RM = W x 36 / (37 - Reps)
    """
    if reps <= 0 or weight_kg <= 0 or reps >= 37:
        return 0.0
    if reps == 1:
        return round(weight_kg, 1)
    return round(weight_kg * 36.0 / (37.0 - reps), 1)


def average_1rm(weight_kg: float, reps: int) -> float:
    """Trung bình 2 công thức — giảm sai số ước lượng."""
    epley = estimate_1rm(weight_kg, reps)
    brzycki = estimate_1rm_brzycki(weight_kg, reps)
    if epley <= 0:
        return brzycki
    if brzycki <= 0:
        return epley
    return round((epley + brzycki) / 2, 1)


#: Bảng %1RM -> số reps tối đa tương ứng (NSCA)
PERCENT_1RM_TABLE: list[tuple[float, int]] = [
    (100, 1), (95, 2), (92.5, 4), (90, 4), (87.5, 6), (85, 6),
    (82.5, 8), (80, 8), (77.5, 10), (75, 10), (72.5, 12), (70, 12),
    (67.5, 15), (65, 15), (60, 20),
]

#: Khuyến nghị vùng tải theo mục tiêu tập luyện
TRAINING_ZONES: dict[str, dict] = {
    "strength": {
        "name": "Sức mạnh tối đa (Max Strength)",
        "percent_range": (85, 95),
        "reps": "1-5",
        "sets": "3-5",
        "rest": "3-5 phút",
        "rpe": "RPE 8-9",
    },
    "hypertrophy": {
        "name": "Phì đại cơ (Hypertrophy)",
        "percent_range": (67, 80),
        "reps": "6-12",
        "sets": "3-5",
        "rest": "60-120 giây",
        "rpe": "RPE 7-9",
    },
    "endurance": {
        "name": "Sức bền cơ (Muscular Endurance)",
        "percent_range": (50, 65),
        "reps": "15-25",
        "sets": "2-4",
        "rest": "30-60 giây",
        "rpe": "RPE 6-7",
    },
    "power": {
        "name": "Sức mạnh bùng nổ (Power)",
        "percent_range": (30, 60),
        "reps": "1-5 (tốc độ tối đa)",
        "sets": "3-6",
        "rest": "2-3 phút",
        "rpe": "RPE 6-7 (nhanh, không mệt)",
    },
}


def reps_for_percent(percent: float) -> int:
    """Tra số reps tối đa tương ứng với %1RM."""
    for limit, reps in PERCENT_1RM_TABLE:
        if percent >= limit:
            return reps
    return 20


def training_load_for_goal(one_rm: float, goal: str) -> dict:
    """Tính tải trọng cụ thể theo mục tiêu từ 1RM."""
    zone_key = {
        "cutting": "hypertrophy",
        "bulking": "hypertrophy",
        "recomp": "hypertrophy",
        "endurance": "endurance",
        "strength": "strength",
    }.get(goal, "hypertrophy")

    zone = TRAINING_ZONES[zone_key]
    low_pct, high_pct = zone["percent_range"]
    return {
        "zone": zone["name"],
        "reps": zone["reps"],
        "sets": zone["sets"],
        "rest": zone["rest"],
        "rpe": zone["rpe"],
        "percent_1rm": f"{low_pct}-{high_pct}%",
        "suggested_weight_low_kg": round(one_rm * low_pct / 100, 1),
        "suggested_weight_high_kg": round(one_rm * high_pct / 100, 1),
    }


# --------------------------------------------------------------------------
# PROGRESSIVE OVERLOAD
# --------------------------------------------------------------------------
#: Bài thân trên tăng 2.5kg, thân dưới tăng 5kg (đơn vị tạ nhỏ nhất khả dụng)
LOWER_BODY_PATTERNS = {"squat", "hinge", "lunge"}
UPPER_INCREMENT_KG = 2.5
LOWER_INCREMENT_KG = 5.0


@dataclass
class OverloadDecision:
    """Kết quả đánh giá tăng tiến cho một bài tập."""

    exercise_name: str
    action: str                     # increase | maintain | decrease | deload
    current_weight_kg: Optional[float]
    suggested_weight_kg: Optional[float]
    increment_kg: float
    reason: str
    confidence: str                 # high | medium | low
    target_reps: str = ""
    notes: list[str] = field(default_factory=list)


def evaluate_progressive_overload(
    exercise_name: str,
    last_sets: list[dict],
    target_reps_upper: int,
    target_rest_seconds: int = 90,
) -> OverloadDecision:
    """Quyết định tăng/giữ/giảm tạ cho buổi kế tiếp.

    Quy tắc nghiệp vụ:
      - Hoàn thành ĐỦ reps ở cận trên của TẤT CẢ các hiệp VÀ RPE trung bình < 8
        -> tăng tạ (2.5kg thân trên / 5kg thân dưới)
      - Hoàn thành đủ reps nhưng RPE >= 8.5 -> giữ tạ, tập thêm 1 buổi
      - Không đủ reps ở hiệp cuối -> giữ tạ
      - Tụt reps nghiêm trọng hoặc RPE 10 -> giảm tạ 5-10%
    """
    ex = EXERCISE_BY_NAME.get(exercise_name)
    is_lower = ex is not None and ex.pattern in LOWER_BODY_PATTERNS
    increment = LOWER_INCREMENT_KG if is_lower else UPPER_INCREMENT_KG

    valid_sets = [s for s in last_sets if (s.get("reps") or 0) > 0]
    if not valid_sets:
        return OverloadDecision(
            exercise_name=exercise_name, action="maintain",
            current_weight_kg=None, suggested_weight_kg=None, increment_kg=increment,
            reason="Chưa có dữ liệu hiệp tập để đánh giá.",
            confidence="low",
        )

    weights = [s.get("weight_kg") for s in valid_sets if s.get("weight_kg")]
    current_weight = round(sum(weights) / len(weights), 1) if weights else None
    reps_list = [s.get("reps") or 0 for s in valid_sets]
    rpes = [s.get("rpe") for s in valid_sets if s.get("rpe") is not None]
    avg_rpe = round(sum(rpes) / len(rpes), 1) if rpes else None

    all_hit_upper = all(r >= target_reps_upper for r in reps_list)
    last_set_hit = reps_list[-1] >= target_reps_upper if reps_list else False

    # --- Không có mức tạ -> chỉ khuyến nghị theo reps ---
    if current_weight is None:
        return OverloadDecision(
            exercise_name=exercise_name, action="maintain",
            current_weight_kg=None, suggested_weight_kg=None, increment_kg=increment,
            reason="Chưa ghi mức tạ. Hãy ghi lại mức tạ mỗi buổi để AI tính tăng tiến.",
            confidence="low",
            notes=["Ghi mức tạ vào Nhật ký tập luyện để nhận gợi ý tăng tải chính xác."],
        )

    # --- RPE quá cao -> giảm tải ---
    if avg_rpe is not None and avg_rpe >= 9.5:
        new_weight = round(current_weight * 0.925 / 2.5) * 2.5
        return OverloadDecision(
            exercise_name=exercise_name, action="decrease",
            current_weight_kg=current_weight, suggested_weight_kg=max(2.5, new_weight),
            increment_kg=increment,
            reason=f"RPE trung bình {avg_rpe} — bạn đang tập sát giới hạn tối đa ở mọi hiệp. "
                   f"Giảm khoảng 7.5% tạ để tích luỹ khối lượng tập chất lượng hơn.",
            confidence="high",
            notes=["Tập sát giới hạn liên tục làm tăng rủi ro chấn thương và cản trở phục hồi."],
        )

    # --- Đủ reps ở tất cả các hiệp ---
    if all_hit_upper:
        if avg_rpe is not None and avg_rpe < 8.0:
            return OverloadDecision(
                exercise_name=exercise_name, action="increase",
                current_weight_kg=current_weight,
                suggested_weight_kg=round(current_weight + increment, 1),
                increment_kg=increment,
                reason=f"Bạn đã hoàn thành đủ {target_reps_upper} reps ở TẤT CẢ "
                       f"{len(valid_sets)} hiệp với RPE trung bình {avg_rpe} — còn dư sức. "
                       f"Tăng {increment}kg ở buổi kế tiếp.",
                confidence="high",
                target_reps=f"{target_reps_upper}",
                notes=[
                    f"Tăng {increment}kg và giữ nguyên mục tiêu {target_reps_upper} reps. "
                    f"Nếu không đủ reps ở mức tạ mới, quay lại mức tạ cũ thêm 1-2 buổi."
                ],
            )
        return OverloadDecision(
            exercise_name=exercise_name, action="maintain",
            current_weight_kg=current_weight, suggested_weight_kg=current_weight,
            increment_kg=increment,
            reason=f"Đã đủ {target_reps_upper} reps nhưng RPE trung bình {avg_rpe} khá cao. "
                   f"Giữ nguyên tạ thêm 1 buổi để củng cố trước khi tăng.",
            confidence="medium",
            notes=["Lặp lại mức tạ này cho tới khi RPE giảm xuống dưới 8 rồi mới tăng."],
        )

    # --- Không đủ reps ở hiệp cuối ---
    if not last_set_hit:
        shortfall = target_reps_upper - reps_list[-1]
        return OverloadDecision(
            exercise_name=exercise_name, action="maintain",
            current_weight_kg=current_weight, suggested_weight_kg=current_weight,
            increment_kg=increment,
            reason=f"Hiệp cuối chỉ đạt {reps_list[-1]}/{target_reps_upper} reps "
                   f"(thiếu {shortfall} reps). Giữ nguyên tạ và cố hoàn thành đủ reps.",
            confidence="high",
            notes=[
                "Chiến lược: tăng thời gian nghỉ thêm 15-30 giây giữa các hiệp, "
                "hoặc giảm 1 hiệp để dồn sức cho các hiệp còn lại."
            ],
        )

    return OverloadDecision(
        exercise_name=exercise_name, action="maintain",
        current_weight_kg=current_weight, suggested_weight_kg=current_weight,
        increment_kg=increment,
        reason="Tiến độ ổn định — tiếp tục duy trì mức tạ hiện tại.",
        confidence="medium",
    )


# --------------------------------------------------------------------------
# DELOAD
# --------------------------------------------------------------------------
#: Sau bao nhiêu tuần tập nặng liên tục thì cần Deload
DELOAD_AFTER_WEEKS = 7
DELOAD_VOLUME_REDUCTION = 0.40      # giảm 40% volume
DELOAD_INTENSITY_REDUCTION = 0.15   # giảm 10-20% tạ


def should_deload(weeks_training: int, deload_count: int = 0) -> bool:
    """Có cần tuần giảm tải hay không (mỗi 6-8 tuần)."""
    effective_weeks = weeks_training - deload_count * DELOAD_AFTER_WEEKS
    return effective_weeks >= DELOAD_AFTER_WEEKS


def build_deload_plan(sessions: list[dict], week_number: int) -> dict:
    """Sinh tuần Deload: giảm 40% số hiệp và 10-20% mức tạ."""
    deload_sessions: list[dict] = []

    for session in sessions:
        new_exercises = []
        for ex in session.get("exercises", []):
            new_exercises.append({
                **ex,
                # Giảm số hiệp ~40% (tối thiểu 2 hiệp)
                "sets": max(2, round(ex.get("sets", 3) * (1 - DELOAD_VOLUME_REDUCTION))),
                "intensity_reduction": f"Giảm {int(DELOAD_INTENSITY_REDUCTION * 100)}% tạ",
                "notes": f"[DELOAD] {ex.get('notes', '')} — tập nhẹ, ưu tiên kỹ thuật và "
                         f"cảm nhận cơ, KHÔNG tập tới giới hạn.",
                "rpe": "RPE 5-6 (chừa 4-5 reps)",
            })

        deload_sessions.append({
            **session,
            "focus": f"[DELOAD] {session.get('focus', '')}",
            "exercises": new_exercises,
            "is_deload": True,
        })

    return {
        "is_deload_week": True,
        "week_number": week_number,
        "volume_reduction_percent": int(DELOAD_VOLUME_REDUCTION * 100),
        "intensity_reduction_percent": int(DELOAD_INTENSITY_REDUCTION * 100),
        "purpose": (
            "Tuần giảm tải (Deload) giúp hệ thần kinh trung ương, khớp và gân phục hồi "
            "sau 6-8 tuần tập nặng liên tục. Bạn vẫn tập đủ buổi nhưng giảm khối lượng "
            "và cường độ — đây là phần bắt buộc của chu kỳ hóa, không phải dấu hiệu lười."
        ),
        "guidance": [
            f"Giảm {int(DELOAD_VOLUME_REDUCTION * 100)}% số hiệp so với tuần thường.",
            f"Giảm {int(DELOAD_INTENSITY_REDUCTION * 100)}% mức tạ (hoặc giữ tạ nhưng "
            f"giảm mạnh số hiệp).",
            "Tập ở RPE 5-6 — dừng khi còn thấy dư sức rõ rệt.",
            "Tăng thời gian nghỉ giữa các hiệp lên 1.5 lần.",
            "Tập trung vào kỹ thuật, biên độ đầy đủ và cảm nhận cơ.",
            "Giữ nguyên tần suất buổi tập, chỉ giảm khối lượng trong buổi.",
            "Sau tuần Deload, quay lại mức tạ cũ và tiếp tục tăng tiến.",
        ],
        "expected_outcome": (
            "Sau tuần Deload, hầu hết mọi người thấy sức mạnh tăng trở lại và cảm giác "
            "cơ tốt hơn. Nếu vẫn mệt mỏi, có thể kéo dài thêm 3-4 ngày nhẹ."
        ),
        "sessions": deload_sessions,
    }


# --------------------------------------------------------------------------
# SMART EXERCISE SWAP — Đổi bài tập tức thì
# --------------------------------------------------------------------------
class SwapReason:
    """Lý do đổi bài — quyết định tiêu chí chọn bài thay thế."""

    EQUIPMENT_BUSY = "equipment_busy"       # máy đang có người dùng
    EQUIPMENT_BROKEN = "equipment_broken"   # máy hỏng / bảo trì
    JOINT_PAIN = "joint_pain"               # tập thấy đau khớp
    NO_EQUIPMENT = "no_equipment"           # không có thiết bị
    TOO_HARD = "too_hard"                   # bài quá khó
    PREFERENCE = "preference"               # không thích bài này

    LABELS = {
        EQUIPMENT_BUSY: "Máy đang có người sử dụng",
        EQUIPMENT_BROKEN: "Máy đang hỏng / bảo trì",
        JOINT_PAIN: "Đang đau khớp khi tập bài này",
        NO_EQUIPMENT: "Không có thiết bị này",
        TOO_HARD: "Bài tập quá khó với trình độ hiện tại",
        PREFERENCE: "Muốn đổi bài khác",
    }


#: Nhóm cơ tương đương để gợi ý đổi bài khi không tìm được cùng pattern
MUSCLE_GROUP_MAP: dict[str, str] = {
    "horizontal_push": "chest",
    "vertical_push": "shoulders",
    "horizontal_pull": "back",
    "vertical_pull": "back",
    "squat": "quads",
    "hinge": "hamstrings",
    "lunge": "legs",
    "isolation": "accessory",
    "core": "core",
}


def find_substitutes(
    exercise_name: str,
    reason: str = SwapReason.PREFERENCE,
    injuries: Optional[list[str]] = None,
    available_equipment: Optional[list[str]] = None,
    broken_equipment_names: Optional[list[str]] = None,
    max_results: int = 4,
) -> dict:
    """Gợi ý bài tập thay thế tương đương — cốt lõi của "Đổi bài tập tức thì".

    Ưu tiên:
      1. Cùng nhóm cơ tác động (pattern giống nhau)
      2. Không xung đột với chấn thương của hội viên
      3. Phù hợp thiết bị đang có
      4. Không nằm trong danh sách máy đang hỏng
      5. Cùng loại compound/isolation để giữ cấu trúc buổi tập
    """
    original = EXERCISE_BY_NAME.get(exercise_name)
    injuries = injuries or []
    broken = [b.lower() for b in (broken_equipment_names or [])]

    if original is None:
        # Không có trong thư viện -> gợi ý theo tên
        candidates = [
            e for e in EXERCISE_LIBRARY
            if exercise_name.split("(")[0].strip().lower() in e.name.lower()
        ]
        if not candidates:
            return {
                "original": exercise_name,
                "reason": reason,
                "reason_label": SwapReason.LABELS.get(reason, reason),
                "substitutes": [],
                "message": (
                    f"Không tìm thấy bài tập '{exercise_name}' trong thư viện. "
                    f"Hãy chọn một bài khác trong lịch tập."
                ),
            }
        original = candidates[0]

    def is_blocked(ex: Exercise) -> bool:
        """Bài có bị chặn bởi chấn thương hoặc máy hỏng hay không."""
        if any(inj in ex.avoid_for for inj in injuries):
            return True
        name_lower = ex.name.lower()
        if any(b in name_lower for b in broken):
            return True
        if available_equipment is not None:
            if not any(eq in available_equipment for eq in ex.equipment):
                return True
        # Loại chính nó
        return ex.name == original.name

    # --- Ưu tiên 1: cùng pattern (cùng nhóm cơ tác động) ---
    same_pattern = [
        e for e in EXERCISE_LIBRARY
        if e.pattern == original.pattern and not is_blocked(e)
    ]

    # --- Ưu tiên 2: cùng nhóm cơ lớn nếu không đủ bài cùng pattern ---
    group = MUSCLE_GROUP_MAP.get(original.pattern)
    same_group = []
    if group and len(same_pattern) < max_results:
        same_group = [
            e for e in EXERCISE_LIBRARY
            if e.pattern != original.pattern
            and MUSCLE_GROUP_MAP.get(e.pattern) == group
            and not is_blocked(e)
        ]

    # Sắp xếp: cùng loại compound/isolation trước, rồi tới bài compound
    def sort_key(ex: Exercise) -> tuple:
        same_type = 0 if ex.is_compound == original.is_compound else 1
        return (same_type, 0 if ex.is_compound else 1, ex.name)

    candidates = sorted(same_pattern, key=sort_key) + sorted(same_group, key=sort_key)

    # Khử trùng lặp, giữ thứ tự
    seen: set[str] = set()
    unique: list[Exercise] = []
    for c in candidates:
        if c.name not in seen:
            seen.add(c.name)
            unique.append(c)

    substitutes = []
    for ex in unique[:max_results]:
        # Tính điểm tương đồng
        similarity = 100
        if ex.pattern != original.pattern:
            similarity -= 25
        if ex.is_compound != original.is_compound:
            similarity -= 15
        if reason == SwapReason.JOINT_PAIN and ex.avoid_for:
            similarity -= 5  # vẫn cảnh báo nếu bài thay thế cũng có rủi ro

        substitutes.append({
            "name": ex.name,
            "target_muscle": ex.target_muscle,
            "type": "Compound (Đa khớp)" if ex.is_compound else "Isolation (Đơn khớp)",
            "movement": ex.pattern,
            "equipment": list(ex.equipment),
            "similarity_percent": max(45, similarity),
            "notes": ex.notes,
            "why": (
                f"Cùng nhóm cơ tác động ({ex.target_muscle})"
                if ex.pattern == original.pattern
                else f"Cùng vùng cơ ({group}) — bài tập bổ trợ tương đương"
            ),
        })

    reason_label = SwapReason.LABELS.get(reason, reason)

    if not substitutes:
        message = (
            f"Không tìm được bài thay thế phù hợp cho '{original.name}' với các ràng buộc "
            f"hiện tại (chấn thương / thiết bị). Hãy hỏi HLV để được hướng dẫn trực tiếp."
        )
    elif reason == SwapReason.JOINT_PAIN:
        message = (
            f"Bạn đang đau khớp khi tập '{original.name}'. Đã gợi ý {len(substitutes)} bài "
            f"thay thế ít áp lực lên khớp hơn. Nếu cơn đau vẫn tiếp diễn với bài mới, "
            f"hãy dừng tập vùng đó và liên hệ HLV."
        )
    elif reason == SwapReason.EQUIPMENT_BROKEN:
        message = (
            f"Máy cho '{original.name}' đang bảo trì. Đã gợi ý {len(substitutes)} bài "
            f"thay thế tương đương để bạn không phải bỏ buổi tập."
        )
    else:
        message = (
            f"Đã gợi ý {len(substitutes)} bài thay thế cho '{original.name}' "
            f"({reason_label.lower()}). Các bài này tác động cùng nhóm cơ nên bạn giữ "
            f"nguyên được cấu trúc buổi tập."
        )

    return {
        "original": original.name,
        "original_muscle": original.target_muscle,
        "reason": reason,
        "reason_label": reason_label,
        "substitutes": substitutes,
        "message": message,
    }


def apply_swap_to_session(
    session_exercises: list[dict],
    exercise_name: str,
    substitute_name: str,
) -> list[dict]:
    """Áp dụng đổi bài vào một buổi tập, giữ nguyên sets/reps/rest."""
    result: list[dict] = []
    for ex in session_exercises:
        if ex.get("name") != exercise_name:
            result.append(ex)
            continue

        new_ex = EXERCISE_BY_NAME.get(substitute_name)
        if new_ex is None:
            result.append(ex)
            continue

        result.append({
            **ex,
            "name": new_ex.name,
            "target_muscle": new_ex.target_muscle,
            "movement": new_ex.pattern,
            "type": "Compound (Đa khớp)" if new_ex.is_compound else "Isolation (Đơn khớp)",
            "notes": new_ex.notes,
            "swapped_from": exercise_name,
            "swap_note": f"Đã đổi từ '{exercise_name}' sang bài này.",
        })
    return result