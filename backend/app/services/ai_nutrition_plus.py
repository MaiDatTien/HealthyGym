"""NUTRITION ENGINE NÂNG CAO — Đổi món tương đương, Carb Cycling & bù trừ Cheat Meal.

Nghiệp vụ:
    1. Macro-Matched Food Swap: đổi thực phẩm nhưng GIỮ NGUYÊN protein và calo.
    2. Carb Cycling: ngày tập nặng ăn cao Carb - ít Fat; ngày nghỉ thấp Carb -
       giữ nguyên Protein.
    3. Cheat Meal Recovery: tính phương án bù trừ khi ăn lố, KHÔNG bắt nhịn đói.
    4. Điều chỉnh calo thông minh khi chững cân / mất cơ.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from app.services.ai_nutrition import FOOD_DB, ALLERGY_REPLACEMENTS


# --------------------------------------------------------------------------
# PHÂN LOẠI THỰC PHẨM THEO VAI TRÒ
# --------------------------------------------------------------------------
#: Nhóm thực phẩm có thể hoán đổi cho nhau (cùng vai trò trong bữa ăn)
FOOD_ROLES: dict[str, list[str]] = {
    "protein_lean": ["uc_ga", "ca_basa", "tom", "thit_heo_nac", "long_trang"],
    "protein_red": ["thit_bo", "thit_heo_nac"],
    "protein_fish": ["ca_hoi", "ca_basa", "ca_thu"],
    "protein_egg": ["trung_ga", "long_trang"],
    "protein_dairy": ["sua_chua_hy_lap", "sua_tuoi", "whey"],
    "protein_plant": ["whey"],
    "carb_complex": ["gao_lut", "khoai_lang", "yen_mach", "banh_mi_nguyen_cam", "khoai_tay"],
    "carb_fast": ["com_trang", "buon", "banh_pho", "chuoi"],
    "fat_healthy": ["dau_oliu", "qua_bo", "hanh_nhan", "hat_dieu", "bo_dau_phong", "dau_me"],
    "veg": ["bong_cai_xanh", "rau_muong", "xa_lach", "ca_chua", "dua_leo"],
    "fruit": ["chuoi", "tao", "cam"],
}

#: Nhãn tiếng Việt cho từng nhóm
ROLE_LABELS: dict[str, str] = {
    "protein_lean": "Đạm nạc (ức gà, cá basa, tôm, thịt heo nạc)",
    "protein_red": "Đạm thịt đỏ (thịt bò, thịt heo nạc)",
    "protein_fish": "Đạm cá (cá hồi, cá basa, cá thu)",
    "protein_egg": "Đạm trứng",
    "protein_dairy": "Đạm từ sữa",
    "protein_plant": "Đạm thực vật / bột",
    "carb_complex": "Tinh bột phức (gạo lứt, khoai lang, yến mạch)",
    "carb_fast": "Tinh bột nhanh (cơm trắng, bún, chuối)",
    "fat_healthy": "Chất béo tốt (dầu oliu, bơ, các loại hạt)",
    "veg": "Rau củ",
    "fruit": "Trái cây",
}


def find_food_role(food_key: str) -> Optional[str]:
    """Xác định vai trò của một thực phẩm trong bữa ăn."""
    for role, keys in FOOD_ROLES.items():
        if food_key in keys:
            return role
    return None


def _is_allergy_safe(food_key: str, allergies: list[str]) -> bool:
    """Thực phẩm có an toàn với dị ứng của hội viên hay không."""
    food = FOOD_DB.get(food_key)
    if not food:
        return False
    tags = food.get("tags", [])
    return not any(a in tags for a in allergies)


# --------------------------------------------------------------------------
# MACRO-MATCHED FOOD SWAP
# --------------------------------------------------------------------------
@dataclass
class FoodSwapOption:
    """Một phương án thay thế thực phẩm."""

    food_key: str
    name: str
    grams: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    delta_calories: float
    delta_protein_g: float
    match_quality: str          # perfect | good | acceptable
    ready_state: str = ""       # sống / chín
    note: str = ""


def _round_portion(grams: float, kcal_per_100g: float) -> float:
    """Làm tròn khẩu phần theo bước hợp lý để dễ cân đong."""
    if kcal_per_100g > 400:          # dầu ăn, bơ đậu phộng, whey
        return max(3, round(grams))
    if grams >= 100:
        return round(grams / 10) * 10
    return max(5, round(grams / 5) * 5)


def suggest_food_swaps(
    food_key: str,
    current_grams: float,
    allergies: Optional[list[str]] = None,
    max_results: int = 5,
    prioritize: str = "protein",   # protein | calories | carbs | fat
) -> dict:
    """Gợi ý thực phẩm thay thế tương đương, tự quy đổi gram để giữ nguyên macro.

    Đây là nghiệp vụ "Đổi thực phẩm tương đương": hội viên không thích ức gà có thể
    đổi sang cá rô phi / thịt bò / tôm mà tổng Protein và Calo KHÔNG ĐỔI.
    """
    allergies = allergies or []
    original = FOOD_DB.get(food_key)
    if not original:
        return {
            "original": food_key,
            "error": f"Không tìm thấy thực phẩm '{food_key}' trong cơ sở dữ liệu.",
            "options": [],
        }

    # Macro mục tiêu cần giữ nguyên
    base_factor = current_grams / 100.0
    target = {
        "calories": original["kcal"] * base_factor,
        "protein_g": original["p"] * base_factor,
        "carbs_g": original["c"] * base_factor,
        "fat_g": original["f"] * base_factor,
    }

    role = find_food_role(food_key)

    # Ứng viên: cùng nhóm vai trò, hoặc cùng nhóm đạm nếu không tìm thấy
    candidate_keys: list[str] = []
    if role:
        candidate_keys.extend(FOOD_ROLES[role])
        # Bổ sung nhóm đạm khác để có nhiều lựa chọn (đổi món linh hoạt)
        if role.startswith("protein"):
            for other_role in ("protein_lean", "protein_red", "protein_fish",
                               "protein_egg", "protein_dairy"):
                if other_role != role:
                    candidate_keys.extend(FOOD_ROLES[other_role])

    # Loại chính nó + thực phẩm gây dị ứng
    candidate_keys = [
        k for k in dict.fromkeys(candidate_keys)
        if k != food_key and k in FOOD_DB and _is_allergy_safe(k, allergies)
    ]

    options: list[FoodSwapOption] = []
    for key in candidate_keys:
        food = FOOD_DB[key]

        # Tính gram để khớp macro ưu tiên
        if prioritize == "protein" and food["p"] > 0:
            grams = (target["protein_g"] / food["p"]) * 100.0
        elif prioritize == "carbs" and food["c"] > 0:
            grams = (target["carbs_g"] / food["c"]) * 100.0
        elif prioritize == "fat" and food["f"] > 0:
            grams = (target["fat_g"] / food["f"]) * 100.0
        elif food["kcal"] > 0:
            grams = (target["calories"] / food["kcal"]) * 100.0
        else:
            continue

        grams = _round_portion(grams, food["kcal"])
        factor = grams / 100.0

        kcal = round(food["kcal"] * factor, 1)
        p = round(food["p"] * factor, 1)
        c = round(food["c"] * factor, 1)
        f = round(food["f"] * factor, 1)

        d_kcal = round(kcal - target["calories"], 1)
        d_p = round(p - target["protein_g"], 1)

        # Đánh giá độ khớp
        pct_kcal = abs(d_kcal) / target["calories"] * 100 if target["calories"] else 0
        pct_p = abs(d_p) / target["protein_g"] * 100 if target["protein_g"] else 0

        if pct_kcal <= 5 and pct_p <= 5:
            quality = "perfect"
        elif pct_kcal <= 12 and pct_p <= 12:
            quality = "good"
        elif pct_kcal <= 22 and pct_p <= 22:
            quality = "acceptable"
        else:
            continue  # lệch quá nhiều -> không phải "tương đương"

        ready_state = "chín" if key in ("gao_lut", "com_trang", "khoai_lang",
                                        "bong_cai_xanh", "rau_muong", "khoai_tay",
                                        "buon", "banh_pho") else "sống"

        options.append(FoodSwapOption(
            food_key=key,
            name=food["name"],
            grams=grams,
            calories=kcal,
            protein_g=p,
            carbs_g=c,
            fat_g=f,
            delta_calories=d_kcal,
            delta_protein_g=d_p,
            match_quality=quality,
            ready_state=ready_state,
            note=(
                f"{grams}g {food['name']} cung cấp tương đương "
                f"{p}g đạm và {round(kcal)} kcal"
            ),
        ))

    # Sắp xếp theo chất lượng khớp
    order = {"perfect": 0, "good": 1, "acceptable": 2}
    options.sort(key=lambda o: (order[o.match_quality], abs(o.delta_calories)))

    return {
        "original": original["name"],
        "original_grams": current_grams,
        "original_macros": {
            "calories": round(target["calories"]),
            "protein_g": round(target["protein_g"], 1),
            "carbs_g": round(target["carbs_g"], 1),
            "fat_g": round(target["fat_g"], 1),
        },
        "role": role,
        "role_label": ROLE_LABELS.get(role or "", ""),
        "prioritize": prioritize,
        "options": [
            {
                "food_key": o.food_key,
                "name": o.name,
                "grams": o.grams,
                "ready_state": o.ready_state,
                "calories": o.calories,
                "protein_g": o.protein_g,
                "carbs_g": o.carbs_g,
                "fat_g": o.fat_g,
                "delta_calories": o.delta_calories,
                "delta_protein_g": o.delta_protein_g,
                "match_quality": o.match_quality,
                "note": o.note,
            }
            for o in options[:max_results]
        ],
        "guidance": [
            "Khẩu phần đã được quy đổi tự động để giữ nguyên protein và calo — "
            "bạn không cần tự tính lại.",
            "Ưu tiên nhóm 'Khớp hoàn hảo' nếu muốn giữ nguyên macro chính xác nhất.",
            "Khi đổi sang thực phẩm có định lượng khác, hãy cân bằng cân điện tử "
            "trong 1-2 tuần đầu để làm quen khẩu phần.",
        ],
    }


# --------------------------------------------------------------------------
# CARB CYCLING
# --------------------------------------------------------------------------
@dataclass
class CarbCyclingDay:
    """Macro của một ngày trong chu kỳ Carb Cycling."""

    day_type: str          # training_heavy | training_light | rest
    label: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    rationale: str = ""


#: Tỷ lệ phân bổ carb theo loại ngày (nhân với carb nền)
CARB_CYCLE_RATIOS = {
    "training_heavy": 1.35,   # ngày tập nặng: cao carb
    "training_light": 1.00,   # ngày tập nhẹ: carb nền
    "rest": 0.60,             # ngày nghỉ: thấp carb
}


def build_carb_cycling(
    base_calories: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    training_days_per_week: int,
    goal: str = "recomp",
) -> dict:
    """Thiết kế chu kỳ Carb Cycling trong tuần.

    Nguyên tắc: ngày tập nặng ăn cao Carb - ít Fat; ngày nghỉ ăn thấp Carb -
    GIỮ NGUYÊN Protein. Tổng calo cả tuần vẫn khớp mục tiêu.
    """
    # Số ngày mỗi loại trong tuần
    heavy_days = min(training_days_per_week, 3)
    light_days = max(0, training_days_per_week - heavy_days)
    rest_days = 7 - training_days_per_week

    def macro_for(day_type: str, day_label: str) -> CarbCyclingDay:
        ratio = CARB_CYCLE_RATIOS[day_type]
        new_carbs = round(carbs_g * ratio)

        # Protein GIỮ NGUYÊN theo đúng nghiệp vụ
        new_protein = protein_g

        # Calo thay đổi theo carb; bù lại bằng fat để giữ tổng calo gần mục tiêu
        carb_delta_kcal = (new_carbs - carbs_g) * 4

        if day_type == "training_heavy":
            # Ngày cao carb: giảm fat để không vượt calo
            new_fat = max(round(fat_g - carb_delta_kcal / 9), round(fat_g * 0.55))
            rationale = (
                "Ngày tập nặng: nạp nhiều tinh bột để đổ đầy glycogen cơ, "
                "giảm chất béo để giữ tổng calo trong mục tiêu. "
                "Đạm giữ nguyên để hỗ trợ phục hồi."
            )
        elif day_type == "rest":
            # Ngày nghỉ: thấp carb, tăng fat bù năng lượng
            new_fat = round(fat_g - carb_delta_kcal / 9)
            new_fat = max(round(fat_g * 0.9), min(new_fat, round(fat_g * 1.6)))
            rationale = (
                "Ngày nghỉ: giảm tinh bột vì cơ không cần glycogen, tăng chất béo "
                "làm nguồn năng lượng chính. Đạm GIỮ NGUYÊN để bảo vệ khối cơ."
            )
        else:
            new_fat = fat_g
            rationale = "Ngày tập nhẹ: giữ nguyên phân bổ macro nền."

        total = new_protein * 4 + new_carbs * 4 + new_fat * 9

        return CarbCyclingDay(
            day_type=day_type,
            label=day_label,
            calories=round(total),
            protein_g=new_protein,
            carbs_g=new_carbs,
            fat_g=new_fat,
            rationale=rationale,
        )

    week: list[CarbCyclingDay] = []
    for i in range(heavy_days):
        week.append(macro_for("training_heavy", f"Ngày tập nặng #{i + 1}"))
    for i in range(light_days):
        week.append(macro_for("training_light", f"Ngày tập nhẹ #{i + 1}"))
    for i in range(rest_days):
        week.append(macro_for("rest", f"Ngày nghỉ #{i + 1}"))

    weekly_calories = sum(d.calories for d in week)
    weekly_target = round(base_calories * 7)

    return {
        "enabled": True,
        "goal": goal,
        "base_macros": {
            "calories": round(base_calories),
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
        },
        "days": [
            {
                "day_type": d.day_type,
                "label": d.label,
                "calories": d.calories,
                "protein_g": d.protein_g,
                "carbs_g": d.carbs_g,
                "fat_g": d.fat_g,
                "rationale": d.rationale,
            }
            for d in week
        ],
        "weekly_totals": {
            "calories": weekly_calories,
            "target_calories": weekly_target,
            "difference": weekly_calories - weekly_target,
            "difference_percent": round(
                (weekly_calories - weekly_target) / weekly_target * 100, 1
            ) if weekly_target else 0,
            "protein_g": sum(d.protein_g for d in week),
        },
        "principles": [
            "PROTEIN GIỮ NGUYÊN mọi ngày — đây là nguyên tắc bất di bất dịch của "
            "Carb Cycling để bảo vệ khối cơ.",
            "Ngày tập nặng: carb cao, fat thấp. Dồn phần lớn carb vào bữa trước và sau tập.",
            "Ngày nghỉ: carb thấp, fat cao hơn để duy trì năng lượng và hormone.",
            "Tổng calo CẢ TUẦN vẫn khớp mục tiêu — Carb Cycling chỉ là cách phân bổ lại, "
            "không phải ăn nhiều hơn.",
            "Phù hợp nhất với mục tiêu Body Recomposition và người tập 4-6 buổi/tuần.",
        ],
        "suitable_for": (
            "Carb Cycling phù hợp khi bạn tập 4-6 buổi/tuần và muốn tăng cơ giảm mỡ "
            "đồng thời. Nếu tập 3 buổi hoặc ít hơn, chế độ macro đều mỗi ngày thường "
            "dễ tuân thủ hơn."
        ),
    }


# --------------------------------------------------------------------------
# BÙ TRỪ CHEAT MEAL
# --------------------------------------------------------------------------
#: Số ngày tối đa để chia nhỏ khoản calo vượt
MAX_COMPENSATION_DAYS = 4
#: Mức giảm calo tối đa mỗi ngày (không được cắt sâu gây đói cực đoan)
MAX_DAILY_DEFICIT = 250
#: Số bước chân tăng thêm mỗi ngày để đốt bù
EXTRA_STEPS_PER_DAY = 2000
#: Calo đốt thêm ước tính cho 2000 bước đi bộ
KCAL_PER_2000_STEPS = 80


def calculate_cheat_meal_compensation(
    excess_calories: float,
    target_calories: float,
    weight_kg: float,
    days_available: int = 4,
    meal_description: str = "",
) -> dict:
    """Tính phương án bù trừ khi hội viên ăn lố — KHÔNG bắt nhịn đói.

    Nguyên tắc nghiệp vụ:
      - Chia nhỏ khoản calo dư ra 3-4 ngày tiếp theo, mỗi ngày giảm nhẹ
      - Tăng thêm hoạt động (đi bộ) thay vì cắt sâu khẩu phần
      - TUYỆT ĐỐI không khuyến nghị nhịn đói hay bỏ bữa
      - Giọng điệu động viên, không trách móc
    """
    excess = max(0.0, excess_calories)
    days = max(1, min(days_available, MAX_COMPENSATION_DAYS))

    # Chia đều khoản dư, nhưng không vượt mức giảm tối đa mỗi ngày
    per_day_from_diet = excess / days
    if per_day_from_diet > MAX_DAILY_DEFICIT:
        per_day_from_diet = MAX_DAILY_DEFICIT
        days = max(1, math.ceil(excess / MAX_DAILY_DEFICIT))
        days = min(days, MAX_COMPENSATION_DAYS)

    per_day_from_diet = round(per_day_from_diet)

    # Phần còn lại bù bằng vận động
    covered_by_diet = per_day_from_diet * days
    remaining = max(0.0, excess - covered_by_diet)
    steps_days_needed = math.ceil(remaining / KCAL_PER_2000_STEPS) if remaining > 0 else 0

    # Sàn an toàn calo
    new_daily_target = round(target_calories - per_day_from_diet)
    floor = 1200.0
    floor_warning = None
    if new_daily_target < floor:
        new_daily_target = int(floor)
        floor_warning = (
            f"Không thể giảm thêm vì mức calo đã chạm sàn an toàn {int(floor)} kcal. "
            f"Phần còn lại sẽ bù hoàn toàn bằng tăng vận động."
        )

    # Ước tính ảnh hưởng cân nặng (1kg mỡ ≈ 7700 kcal)
    weight_impact_g = round(excess / 7700 * 1000)

    return {
        "excess_calories": round(excess),
        "meal_description": meal_description,
        "compensation_plan": {
            "days": days,
            "daily_calorie_reduction": per_day_from_diet,
            "new_daily_target": new_daily_target,
            "extra_steps_per_day": EXTRA_STEPS_PER_DAY,
            "extra_steps_note": (
                f"Thêm {EXTRA_STEPS_PER_DAY:,} bước chân mỗi ngày "
                f"(≈ {KCAL_PER_2000_STEPS} kcal/ngày) trong {days} ngày tới."
            ).replace(",", "."),
            "steps_days_if_needed": steps_days_needed,
            "total_covered_by_diet": covered_by_diet,
            "total_covered_by_activity": min(remaining, steps_days_needed * KCAL_PER_2000_STEPS),
        },
        "weight_impact": {
            "grams": weight_impact_g,
            "explanation": (
                f"{round(excess)} kcal vượt mức tương đương khoảng {weight_impact_g}g mỡ "
                f"nếu không bù trừ (1kg mỡ ≈ 7.700 kcal)."
            ),
            "reassurance": (
                "Một bữa ăn lố KHÔNG phá hỏng kết quả của cả tuần. Điều quan trọng là "
                "cách bạn xử lý những ngày tiếp theo — bù trừ nhẹ nhàng và quay lại "
                "đúng kế hoạch."
            ),
        },
        "floor_warning": floor_warning,
        "tone_message": (
            f"Không sao cả! Một bữa ăn thoải mái là phần bình thường của cuộc sống và "
            f"thực tế còn giúp tinh thần thoải mái hơn. Chúng ta chỉ cần điều chỉnh nhẹ "
            f"trong {days} ngày tới: mỗi ngày giảm {per_day_from_diet} kcal "
            f"(vẫn đủ ăn no với đạm và rau) và đi bộ thêm {EXTRA_STEPS_PER_DAY:,} bước. "
            f"Tuyệt đối KHÔNG nhịn đói hay bỏ bữa — làm vậy chỉ khiến bạn mệt và dễ ăn "
            f"bù nhiều hơn."
        ).replace(",", "."),
        "do_not": [
            "KHÔNG nhịn đói hoàn toàn ngày hôm sau.",
            "KHÔNG bỏ bữa sáng để 'bù' calo.",
            "KHÔNG tập cardio cực nặng để trừng phạt bản thân.",
            "KHÔNG cắt đạm — đạm luôn giữ nguyên để bảo vệ khối cơ.",
            "KHÔNG tự trách móc — một bữa ăn không quyết định kết quả dài hạn.",
        ],
        "do_this": [
            f"Giảm nhẹ {per_day_from_diet} kcal/ngày trong {days} ngày — cắt từ tinh bột "
            f"và chất béo, KHÔNG cắt đạm.",
            f"Đi bộ thêm {EXTRA_STEPS_PER_DAY:,} bước mỗi ngày.".replace(",", "."),
            "Uống đủ nước (3-3.5 lít) để hỗ trợ chuyển hoá và giảm cảm giác thèm ăn.",
            "Ưu tiên rau xanh và đạm nạc trong các bữa tiếp theo để no lâu hơn.",
            "Quay lại đúng kế hoạch bình thường sau khi hết giai đoạn bù trừ.",
        ],
    }


# --------------------------------------------------------------------------
# ĐIỀU CHỈNH CALO THÔNG MINH (PLATEAU / MUSCLE LOSS)
# --------------------------------------------------------------------------
@dataclass
class CalorieAdjustment:
    """Kết quả điều chỉnh calo."""

    action: str                 # calorie_cut | calorie_increase | cardio_add | refeed | deload | maintain
    calorie_delta: float
    new_target_calories: float
    reason: str
    detail: list[str] = field(default_factory=list)
    monitoring: list[str] = field(default_factory=list)


def adjust_for_plateau(
    current_target_calories: float,
    weeks_stalled: int,
    adherence_percent: float,
    current_cardio_minutes: int = 0,
) -> CalorieAdjustment:
    """Xử lý chững cân: giảm 150-200 kcal hoặc tăng 10 phút cardio."""
    if adherence_percent < 80:
        return CalorieAdjustment(
            action="maintain",
            calorie_delta=0,
            new_target_calories=current_target_calories,
            reason=(
                f"Mức tuân thủ chỉ {adherence_percent}% — chưa đủ để kết luận chững cân. "
                f"Chưa nên giảm calo thêm."
            ),
            detail=[
                "Chững cân chỉ được xác định khi bạn tuân thủ đúng từ 80% trở lên "
                "trong ít nhất 2 tuần liên tiếp.",
                f"Hãy tập trung cải thiện độ chính xác khi cân đong và ghi nhật ký "
                f"trước khi cắt giảm thêm calo.",
            ],
            monitoring=["Ghi đầy đủ nhật ký ăn uống trong 7 ngày tới."],
        )

    # Ưu tiên tăng cardio trước khi cắt calo sâu (bảo vệ khối cơ tốt hơn)
    if current_cardio_minutes < 30 and weeks_stalled >= 2:
        return CalorieAdjustment(
            action="cardio_add",
            calorie_delta=0,
            new_target_calories=current_target_calories,
            reason=(
                f"Chững cân {weeks_stalled} tuần với mức tuân thủ tốt ({adherence_percent}%). "
                f"Ưu tiên tăng vận động trước khi cắt calo — cách này bảo vệ khối cơ tốt hơn."
            ),
            detail=[
                f"Thêm 10 phút LISS (đi bộ dốc) vào cuối mỗi buổi tập, "
                f"hoặc tăng 2.000 bước chân/ngày.",
                "Giữ nguyên calo nạp trong 1-2 tuần để xem cơ thể phản ứng.",
                "Nếu sau 2 tuần vẫn chững, mới giảm 150-200 kcal.",
            ],
            monitoring=[
                "Theo dõi cân nặng trung bình tuần (cân 3-4 lần, lấy trung bình).",
                "Đo vòng eo mỗi tuần — đôi khi mỡ giảm nhưng cân nặng không đổi.",
            ],
        )

    # Cắt calo nhẹ
    cut = 175.0
    new_target = max(1200.0, current_target_calories - cut)
    actual_cut = current_target_calories - new_target

    detail = [
        f"Giảm {round(actual_cut)} kcal/ngày (trong khoảng khuyến nghị 150-200 kcal).",
        "Cắt từ tinh bột và chất béo — GIỮ NGUYÊN đạm để bảo vệ khối cơ.",
        "Nếu đã ăn kiêng liên tục trên 8 tuần, cân nhắc 1 ngày Refeed "
        "(ăn ngang TDEE với carb cao) để nạp lại leptin.",
    ]

    if weeks_stalled >= 4:
        detail.append(
            f"Đã chững {weeks_stalled} tuần — nên cân nhắc 1 ngày Refeed/tuần "
            f"trước khi cắt sâu thêm, vì hormone leptin có thể đã xuống thấp."
        )

    return CalorieAdjustment(
        action="calorie_cut",
        calorie_delta=-round(actual_cut),
        new_target_calories=round(new_target),
        reason=(
            f"Chững cân {weeks_stalled} tuần liên tiếp với mức tuân thủ {adherence_percent}% "
            f"và đã có cardio ở mức hợp lý."
        ),
        detail=detail,
        monitoring=[
            "Theo dõi trong 2 tuần trước khi điều chỉnh tiếp.",
            "Nếu sụt quá nhanh (trên 1%/tuần), tăng lại 100-150 kcal.",
        ],
    )


def adjust_for_muscle_loss(
    current_target_calories: float,
    weekly_weight_change_percent: float,
    strength_dropped: bool,
    weeks_in_deficit: int,
) -> CalorieAdjustment:
    """Xử lý mất cơ / quá tải: tăng lại 200 kcal từ carb và protein."""
    if weekly_weight_change_percent >= -1.5 and not strength_dropped:
        return CalorieAdjustment(
            action="maintain",
            calorie_delta=0,
            new_target_calories=current_target_calories,
            reason="Tốc độ giảm cân và sức mạnh đều trong ngưỡng an toàn.",
            detail=["Tiếp tục duy trì kế hoạch hiện tại."],
            monitoring=["Theo dõi sức mạnh mỗi buổi tập để phát hiện sớm dấu hiệu mất cơ."],
        )

    reasons: list[str] = []
    if weekly_weight_change_percent < -1.5:
        reasons.append(
            f"cân nặng giảm {abs(weekly_weight_change_percent)}%/tuần "
            f"(vượt ngưỡng an toàn 1%/tuần)"
        )
    if strength_dropped:
        reasons.append("mức tạ tập bị tụt giảm")

    increase = 200.0
    # Nếu đã thâm hụt quá lâu, tăng nhiều hơn
    if weeks_in_deficit >= 12:
        increase = 300.0

    return CalorieAdjustment(
        action="calorie_increase",
        calorie_delta=increase,
        new_target_calories=round(current_target_calories + increase),
        reason=f"Phát hiện dấu hiệu mất cơ: {', '.join(reasons)}.",
        detail=[
            f"Tăng lại {round(increase)} kcal/ngày — phân bổ 100 kcal vào Carb "
            f"và 100 kcal vào Protein.",
            "Giữ nguyên khối lượng và cường độ tập luyện, không giảm tạ.",
            "Đảm bảo ngủ đủ 7.5-9 tiếng — thiếu ngủ làm tăng mất cơ trong thâm hụt calo.",
            "Kiểm tra lại lượng đạm: cần tối thiểu 2.0-2.2g/kg cân nặng khi giảm mỡ.",
        ],
        monitoring=[
            "Theo dõi sức mạnh ở các bài compound chính mỗi tuần.",
            "Nếu mức tạ phục hồi trong 1-2 tuần, giữ mức calo mới.",
            f"Đã ở thâm hụt {weeks_in_deficit} tuần — cân nhắc giai đoạn duy trì "
            f"(Diet Break) 1-2 tuần ở mức TDEE.",
        ],
    )


def build_weekly_recalibration(
    *,
    current_target_calories: float,
    base_tdee: float,
    weekly_weight_change_percent: float,
    weeks_stalled: int,
    adherence_percent: float,
    strength_dropped: bool,
    weeks_in_deficit: int,
    current_cardio_minutes: int = 0,
    hunger_level: Optional[int] = None,
    sleep_quality: Optional[int] = None,
) -> dict:
    """Bộ điều phối hiệu chỉnh động — quyết định điều chỉnh nào được áp dụng."""
    # Ưu tiên 1: an toàn (mất cơ) trước hiệu quả (chững cân)
    if weekly_weight_change_percent < -1.5 or strength_dropped:
        adjustment = adjust_for_muscle_loss(
            current_target_calories, weekly_weight_change_percent,
            strength_dropped, weeks_in_deficit,
        )
        issue = "muscle_loss"
    elif weeks_stalled >= 2:
        adjustment = adjust_for_plateau(
            current_target_calories, weeks_stalled, adherence_percent,
            current_cardio_minutes,
        )
        issue = "plateau"
    else:
        adjustment = CalorieAdjustment(
            action="maintain",
            calorie_delta=0,
            new_target_calories=current_target_calories,
            reason="Tiến độ đang đúng hướng — không cần điều chỉnh.",
            detail=["Tiếp tục duy trì kế hoạch hiện tại."],
        )
        issue = "on_track"

    # Cảnh báo phụ từ dữ liệu chủ quan
    extra_notes: list[str] = []
    if hunger_level is not None and hunger_level >= 4:
        extra_notes.append(
            f"Mức độ đói cao ({hunger_level}/5) — tăng khối lượng rau xanh và "
            f"chia nhỏ bữa ăn để giảm cảm giác đói mà không tăng calo."
        )
    if sleep_quality is not None and sleep_quality <= 2:
        extra_notes.append(
            f"Chất lượng giấc ngủ kém ({sleep_quality}/5) — thiếu ngủ làm tăng cortisol, "
            f"tăng cảm giác đói và đẩy nhanh mất cơ. Ưu tiên cải thiện giấc ngủ trước khi "
            f"cắt calo thêm."
        )
    if weeks_in_deficit >= 12 and adjustment.action in ("calorie_cut", "cardio_add"):
        extra_notes.append(
            f"Đã thâm hụt {weeks_in_deficit} tuần liên tục — nên có giai đoạn Diet Break "
            f"1-2 tuần ăn ngang TDEE để phục hồi hormone và tâm lý trước khi tiếp tục."
        )

    # Đánh giá tổng thể
    if issue == "muscle_loss":
        feedback = (
            f"⚠️ Tôi phát hiện dấu hiệu bạn đang mất cơ chứ không chỉ mất mỡ. "
            f"Đây là điều cần xử lý ngay vì khối cơ rất khó xây lại. "
            f"{adjustment.reason} Tôi đã tăng lại {round(adjustment.calorie_delta)} kcal "
            f"cho bạn — hãy ăn đủ và tiếp tục tập tạ nặng, đừng giảm tạ."
        )
    elif issue == "plateau":
        feedback = (
            f"Chững cân là hiện tượng hoàn toàn bình thường trong quá trình giảm mỡ — "
            f"cơ thể đã thích nghi với mức năng lượng hiện tại. "
            f"{adjustment.reason} Kế hoạch điều chỉnh đã được cập nhật bên dưới."
        )
    else:
        feedback = (
            f"Tiến độ của bạn đang tốt! Cân nặng thay đổi "
            f"{weekly_weight_change_percent}%/tuần, nằm trong ngưỡng an toàn. "
            f"Hãy tiếp tục duy trì sự nhất quán."
        )

    return {
        "issue_detected": issue,
        "adjustment": {
            "action": adjustment.action,
            "calorie_delta": adjustment.calorie_delta,
            "new_target_calories": adjustment.new_target_calories,
            "reason": adjustment.reason,
            "detail": adjustment.detail,
        },
        "extra_notes": extra_notes,
        "monitoring": adjustment.monitoring,
        "ai_feedback": feedback,
        "next_checkin_note": (
            "Cập nhật lại cân nặng trung bình tuần và số buổi tập thực tế vào Chủ Nhật "
            "tuần sau để tôi đánh giá lại hiệu quả điều chỉnh."
        ),
    }