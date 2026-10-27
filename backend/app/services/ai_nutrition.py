"""AI NUTRITION & RECOVERY PLANNER — Chế độ dinh dưỡng, thực đơn & phục hồi.

Nghiệp vụ:
    1. Calo mục tiêu:
         Cutting  : TDEE - 300 đến 500 kcal
         Bulking  : TDEE + 200 đến 300 kcal
         Recomp   : TDEE hoặc thâm hụt nhẹ 100-200 kcal
         Endurance: TDEE (duy trì)
    2. Phân bổ đa lượng (Macros):
         Protein : 1.8-2.2 g/kg cân nặng (hoặc 2.2-2.5 g/kg LBM)
         Fat     : 20-30% tổng calo
         Carbs   : phần calo còn lại
    3. Thực đơn mẫu 4 bữa với thực phẩm thuần Việt, định lượng gram sống.
    4. Nước: Cân nặng x 0.04 lít + 500ml mỗi giờ tập.
    5. Nghỉ ngơi & phục hồi: giấc ngủ, ngày nghỉ, NEAT, thực phẩm bổ sung.
"""
from __future__ import annotations

import math
from typing import Optional


# --------------------------------------------------------------------------
# CƠ SỞ DỮ LIỆU THỰC PHẨM VIỆT NAM
# (Giá trị trên 100g phần ăn được; ưu tiên số liệu thực phẩm sống/khô)
# --------------------------------------------------------------------------
FOOD_DB: dict[str, dict] = {
    # --- Đạm động vật ---
    "uc_ga": {"name": "Ức gà áp chảo (sống)", "kcal": 165, "p": 31.0, "c": 0.0, "f": 3.6, "tags": []},
    "thit_bo": {"name": "Thịt thăn bò (sống)", "kcal": 217, "p": 26.0, "c": 0.0, "f": 11.8, "tags": []},
    "thit_heo_nac": {"name": "Thịt heo nạc thăn (sống)", "kcal": 143, "p": 26.0, "c": 0.0, "f": 3.5, "tags": []},
    "ca_hoi": {"name": "Cá hồi phi lê (sống)", "kcal": 208, "p": 20.0, "c": 0.0, "f": 13.0, "tags": ["fish", "seafood"]},
    "ca_basa": {"name": "Cá basa phi lê (sống)", "kcal": 90, "p": 16.5, "c": 0.0, "f": 2.5, "tags": ["fish", "seafood"]},
    "ca_thu": {"name": "Cá thu (sống)", "kcal": 205, "p": 19.0, "c": 0.0, "f": 13.9, "tags": ["fish", "seafood"]},
    "tom": {"name": "Tôm tươi bóc vỏ (sống)", "kcal": 99, "p": 24.0, "c": 0.2, "f": 0.3, "tags": ["seafood"]},
    "trung_ga": {"name": "Trứng gà nguyên quả", "kcal": 155, "p": 13.0, "c": 1.1, "f": 11.0, "tags": ["egg"]},
    "long_trang": {"name": "Lòng trắng trứng gà", "kcal": 52, "p": 11.0, "c": 0.7, "f": 0.2, "tags": ["egg"]},
    "sua_tuoi": {"name": "Sữa tươi không đường", "kcal": 62, "p": 3.2, "c": 4.8, "f": 3.2, "tags": ["dairy", "lactose"]},
    "sua_chua_hy_lap": {"name": "Sữa chua Hy Lạp không đường", "kcal": 59, "p": 10.0, "c": 3.6, "f": 0.4, "tags": ["dairy", "lactose"]},
    "whey": {"name": "Whey Protein (bột)", "kcal": 400, "p": 80.0, "c": 8.0, "f": 5.0, "tags": ["dairy", "lactose"]},

    # --- Tinh bột ---
    "gao_lut": {"name": "Cơm gạo lứt (chín)", "kcal": 110, "p": 2.6, "c": 23.0, "f": 0.9, "tags": []},
    "com_trang": {"name": "Cơm trắng (chín)", "kcal": 130, "p": 2.7, "c": 28.0, "f": 0.3, "tags": []},
    "khoai_lang": {"name": "Khoai lang luộc", "kcal": 86, "p": 1.6, "c": 20.0, "f": 0.1, "tags": []},
    "yen_mach": {"name": "Yến mạch cán dẹt", "kcal": 389, "p": 16.9, "c": 66.3, "f": 6.9, "tags": ["gluten"]},
    "banh_mi_nguyen_cam": {"name": "Bánh mì nguyên cám", "kcal": 247, "p": 13.0, "c": 41.0, "f": 3.4, "tags": ["gluten"]},
    "khoai_tay": {"name": "Khoai tây luộc", "kcal": 87, "p": 2.0, "c": 20.0, "f": 0.1, "tags": []},
    "buon": {"name": "Bún tươi", "kcal": 110, "p": 2.2, "c": 25.0, "f": 0.2, "tags": []},
    "banh_pho": {"name": "Bánh phở tươi", "kcal": 128, "p": 3.5, "c": 28.0, "f": 0.3, "tags": []},

    # --- Chất béo tốt ---
    "dau_oliu": {"name": "Dầu oliu nguyên chất", "kcal": 884, "p": 0.0, "c": 0.0, "f": 100.0, "tags": []},
    "bo_dau_phong": {"name": "Bơ đậu phộng tự nhiên", "kcal": 588, "p": 25.0, "c": 20.0, "f": 50.0, "tags": ["peanut"]},
    "hat_dieu": {"name": "Hạt điều rang", "kcal": 553, "p": 18.0, "c": 30.0, "f": 44.0, "tags": ["nut"]},
    "hanh_nhan": {"name": "Hạnh nhân", "kcal": 579, "p": 21.0, "c": 22.0, "f": 50.0, "tags": ["nut"]},
    "qua_bo": {"name": "Quả bơ", "kcal": 160, "p": 2.0, "c": 9.0, "f": 15.0, "tags": []},
    "dau_me": {"name": "Mè (vừng) rang", "kcal": 573, "p": 17.0, "c": 23.0, "f": 50.0, "tags": []},

    # --- Rau củ & trái cây ---
    "bong_cai_xanh": {"name": "Bông cải xanh luộc", "kcal": 35, "p": 2.4, "c": 7.0, "f": 0.4, "tags": []},
    "rau_muong": {"name": "Rau muống luộc", "kcal": 20, "p": 2.5, "c": 3.0, "f": 0.2, "tags": []},
    "xa_lach": {"name": "Xà lách & rau trộn", "kcal": 15, "p": 1.4, "c": 2.9, "f": 0.2, "tags": []},
    "ca_chua": {"name": "Cà chua", "kcal": 18, "p": 0.9, "c": 3.9, "f": 0.2, "tags": []},
    "dua_leo": {"name": "Dưa leo", "kcal": 15, "p": 0.7, "c": 3.6, "f": 0.1, "tags": []},
    "chuoi": {"name": "Chuối chín", "kcal": 89, "p": 1.1, "c": 23.0, "f": 0.3, "tags": []},
    "tao": {"name": "Táo", "kcal": 52, "p": 0.3, "c": 14.0, "f": 0.2, "tags": []},
    "cam": {"name": "Cam", "kcal": 47, "p": 0.9, "c": 12.0, "f": 0.1, "tags": []},
    "việt_quất": {"name": "Việt quất", "kcal": 57, "p": 0.7, "c": 14.0, "f": 0.3, "tags": []},
    "gao_lut_trang_mieng": {"name": "Bánh gạo lứt", "kcal": 380, "p": 8.0, "c": 80.0, "f": 3.0, "tags": []},
}

#: Thực phẩm thay thế theo từng nhóm dị ứng
ALLERGY_REPLACEMENTS: dict[str, dict[str, str]] = {
    "fish":    {"ca_hoi": "uc_ga", "ca_basa": "uc_ga", "ca_thu": "uc_ga"},
    "seafood": {"tom": "uc_ga", "ca_hoi": "thit_bo", "ca_basa": "uc_ga", "ca_thu": "thit_bo"},
    "egg":     {"trung_ga": "uc_ga", "long_trang": "uc_ga"},
    "dairy":   {"sua_tuoi": "sua_hanh_nhan", "sua_chua_hy_lap": "sua_hanh_nhan", "whey": "uc_ga"},
    "lactose": {"sua_tuoi": "sua_hanh_nhan", "sua_chua_hy_lap": "sua_hanh_nhan", "whey": "long_trang"},
    "peanut":  {"bo_dau_phong": "hat_dieu"},
    "nut":     {"hat_dieu": "dau_me", "hanh_nhan": "dau_me"},
    "gluten":  {"yen_mach": "gao_lut", "banh_mi_nguyen_cam": "khoai_lang"},
    "soy":     {},
}

# Bổ sung thực phẩm thay thế không gây dị ứng
FOOD_DB["sua_hanh_nhan"] = {
    "name": "Sữa hạnh nhân không đường", "kcal": 17, "p": 0.6, "c": 0.6, "f": 1.2, "tags": ["nut"],
}


# --------------------------------------------------------------------------
# KHUNG THỰC ĐƠN THAM CHIẾU (thiết kế cho ~2000 kcal / 150g đạm)
# --------------------------------------------------------------------------
MEAL_TEMPLATES: list[dict] = [
    {
        "meal_name": "Bữa sáng",
        "time": "07:00",
        "reference_kcal": 480,
        "items": [
            ("yen_mach", 60),
            ("trung_ga", 100),
            ("sua_tuoi", 200),
            ("chuoi", 100),
        ],
        "tip": "Ăn trong vòng 60 phút sau khi thức dậy để ổn định đường huyết và nạp đạm sớm.",
    },
    {
        "meal_name": "Bữa trưa",
        "time": "12:00",
        "reference_kcal": 640,
        "items": [
            ("uc_ga", 200),
            ("gao_lut", 200),
            ("bong_cai_xanh", 200),
            ("dau_oliu", 7),
        ],
        "tip": "Chia đĩa theo tỉ lệ: 1/2 rau, 1/4 đạm, 1/4 tinh bột phức để kiểm soát calo dễ dàng.",
    },
    {
        "meal_name": "Bữa phụ trước tập (Pre-workout)",
        "time": "16:30",
        "reference_kcal": 230,
        "items": [
            ("chuoi", 120),
            ("whey", 30),
        ],
        "tip": "Ăn trước tập 60-90 phút. Carb nhanh + đạm dễ tiêu giúp tăng hiệu suất buổi tập.",
    },
    {
        "meal_name": "Bữa tối sau tập (Post-workout)",
        "time": "19:30",
        "reference_kcal": 640,
        "items": [
            ("ca_hoi", 180),
            ("khoai_lang", 200),
            ("xa_lach", 150),
            ("dau_oliu", 7),
        ],
        "tip": "Nạp đạm trong vòng 2 giờ sau tập để tối ưu tổng hợp protein cơ bắp (MPS). "
               "Cá hồi giàu Omega-3 giúp giảm viêm và hỗ trợ phục hồi khớp.",
    },
]

#: Thực đơn cho mục tiêu Bulking (thêm bữa phụ thứ 5)
BULKING_EXTRA_MEAL: dict = {
    "meal_name": "Bữa phụ tối (Trước khi ngủ)",
    "time": "21:30",
    "reference_kcal": 300,
    "items": [
        ("sua_chua_hy_lap", 200),
        ("hanh_nhan", 30),
    ],
    "tip": "Casein từ sữa chua Hy Lạp tiêu hoá chậm, hỗ trợ phục hồi cơ trong lúc ngủ.",
}

#: Thực đơn cho mục tiêu Cutting (bỏ bữa phụ, giảm tinh bột)
CUTTING_ADJUSTMENTS: dict[str, float] = {
    "gao_lut": 0.75,
    "khoai_lang": 0.75,
    "yen_mach": 0.8,
    "dau_oliu": 0.6,
}


# --------------------------------------------------------------------------
# TÍNH MACROS
# --------------------------------------------------------------------------
def calc_target_calories(tdee: float, goal: str, body_fat_pct: float) -> tuple[float, float]:
    """Trả về (calo mục tiêu, mức điều chỉnh so với TDEE)."""
    if goal == "cutting":
        # Thâm hụt sâu hơn nếu mỡ nhiều, nông hơn nếu đã gầy
        if body_fat_pct >= 25:
            adj = -500
        elif body_fat_pct >= 18:
            adj = -400
        else:
            adj = -300
    elif goal == "bulking":
        adj = 300 if body_fat_pct < 15 else 200
    elif goal == "recomp":
        adj = -150
    else:  # endurance
        adj = 0

    target = tdee + adj
    # Sàn an toàn: không bao giờ khuyến nghị dưới 1200 kcal (nữ) / 1500 (nam)
    floor = 1200.0
    if target < floor:
        target = floor
        adj = round(target - tdee, 1)
    return round(target, 0), adj


def calc_macros(
    target_calories: float,
    weight_kg: float,
    lbm_kg: float,
    goal: str,
    body_fat_pct: float,
) -> dict:
    """Tính Protein / Carb / Fat theo gram và kcal."""
    # --- Protein: 1.8-2.2 g/kg cân nặng, hoặc 2.2-2.5 g/kg LBM ---
    if goal == "cutting":
        # Giảm mỡ cần đạm cao nhất để bảo toàn cơ
        protein_per_kg = 2.2 if body_fat_pct >= 20 else 2.0
    elif goal == "bulking":
        protein_per_kg = 1.9
    elif goal == "recomp":
        protein_per_kg = 2.1
    else:
        protein_per_kg = 1.8

    # Hai quy tắc nghiệp vụ cùng tồn tại:
    #   (a) 1.8 - 2.2 g/kg CÂN NẶNG     — nguyên tắc chung
    #   (b) 2.2 - 2.5 g/kg KHỐI CƠ NẠC  — tinh chỉnh, vì khối mỡ không cần đạm
    # Với người thừa mỡ nhiều, hai khoảng này có thể KHÔNG giao nhau (khối mỡ lớn
    # làm cận trên của (b) thấp hơn cận dưới của (a)). Khi đó ưu tiên SÀN theo cân
    # nặng: khuyến nghị thiếu đạm gây mất cơ là rủi ro lớn hơn khuyến nghị dư nhẹ.
    protein_g = round(weight_kg * protein_per_kg)
    lower_bound = max(math.ceil(weight_kg * 1.8), math.ceil(lbm_kg * 2.2))
    upper_bound = min(round(weight_kg * 2.2), math.floor(lbm_kg * 2.5))

    protein_g = lower_bound if lower_bound > upper_bound else min(
        max(protein_g, lower_bound), upper_bound
    )

    # --- Fat: 20-30% tổng calo ---
    fat_ratio = 0.25 if goal in ("cutting", "recomp") else 0.27
    fat_g = round((target_calories * fat_ratio) / 9.0)

    # Sàn chất béo an toàn cho hormone (0.6 g/kg)
    fat_g = max(fat_g, round(weight_kg * 0.6))

    # --- Carbs: phần calo còn lại ---
    remaining = target_calories - (protein_g * 4) - (fat_g * 9)
    if remaining < 0:
        # Ưu tiên giữ đạm và mỡ tối thiểu, cắt bớt carb
        carbs_g = 50
        fat_g = max(round(weight_kg * 0.5), 30)
        remaining = target_calories - (protein_g * 4) - (fat_g * 9)
        carbs_g = max(30, round(remaining / 4.0))
    else:
        carbs_g = round(remaining / 4.0)

    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    carbs_kcal = carbs_g * 4
    total_kcal = protein_kcal + fat_kcal + carbs_kcal

    return {
        "protein_grams": protein_g,
        "carbs_grams": carbs_g,
        "fat_grams": fat_g,
        "protein_kcal": round(protein_kcal),
        "carbs_kcal": round(carbs_kcal),
        "fat_kcal": round(fat_kcal),
        "protein_percent": round(protein_kcal / total_kcal * 100) if total_kcal else 0,
        "carbs_percent": round(carbs_kcal / total_kcal * 100) if total_kcal else 0,
        "fat_percent": round(fat_kcal / total_kcal * 100) if total_kcal else 0,
        "protein_per_kg": round(protein_g / weight_kg, 2),
        "protein_per_kg_lbm": round(protein_g / lbm_kg, 2),
        "total_calories": round(total_kcal),
    }


# --------------------------------------------------------------------------
# SINH THỰC ĐƠN
# --------------------------------------------------------------------------
def _resolve_food(food_key: str, allergies: list[str]) -> tuple[str, str | None]:
    """Xử lý dị ứng: trả về (food_key, tên gốc đã thay thế nếu có)."""
    food = FOOD_DB.get(food_key)
    if not food:
        return food_key, None
    for allergy in allergies:
        if allergy in food.get("tags", []):
            replacement = ALLERGY_REPLACEMENTS.get(allergy, {}).get(food_key)
            if replacement and replacement in FOOD_DB:
                return replacement, food["name"]
    return food_key, None


def build_meal_plan(
    target_calories: float,
    macros: dict,
    goal: str,
    allergies: Optional[list[str]] = None,
) -> tuple[list[dict], list[str]]:
    """Sinh thực đơn 4-5 bữa, định lượng gram theo calo mục tiêu.

    Trả về (danh sách bữa ăn, danh sách ghi chú thay thế do dị ứng).
    """
    allergies = allergies or []
    templates = [dict(t) for t in MEAL_TEMPLATES]
    if goal == "bulking":
        templates.append(dict(BULKING_EXTRA_MEAL))

    # Tỷ lệ phân bổ calo cho từng bữa (theo template gốc)
    ref_total = sum(t["reference_kcal"] for t in templates)
    scale = target_calories / ref_total if ref_total else 1.0

    meals: list[dict] = []
    substitutions: list[str] = []

    for tpl in templates:
        foods_display: list[str] = []
        meal_kcal = 0.0
        meal_p = 0.0
        meal_c = 0.0
        meal_f = 0.0

        target_meal_kcal = tpl["reference_kcal"] * scale

        # Tính calo gốc của template để suy ra hệ số định lượng
        base_kcal = sum(
            FOOD_DB[k]["kcal"] * g / 100.0
            for k, g in tpl["items"] if k in FOOD_DB
        )
        portion_factor = (target_meal_kcal / base_kcal) if base_kcal else 1.0

        for food_key, grams in tpl["items"]:
            resolved_key, replaced_name = _resolve_food(food_key, allergies)
            if replaced_name:
                new_name = FOOD_DB[resolved_key]["name"]
                substitutions.append(
                    f"Món '{replaced_name}' đã được thay bằng '{new_name}' do dị ứng của bạn."
                )
            food = FOOD_DB.get(resolved_key)
            if not food:
                continue

            # Cutting: giảm khẩu phần tinh bột/chất béo
            item_scale = portion_factor
            if goal == "cutting" and resolved_key in CUTTING_ADJUSTMENTS:
                item_scale *= CUTTING_ADJUSTMENTS[resolved_key]

            adjusted = grams * item_scale
            # Làm tròn theo bước hợp lý để dễ cân đong
            if food["kcal"] > 400:          # dầu ăn, bơ đậu phộng, whey
                adjusted = max(3, round(adjusted))
                unit = "g"
            elif adjusted >= 100:
                adjusted = round(adjusted / 10) * 10
                unit = "g"
            else:
                adjusted = round(adjusted / 5) * 5
                unit = "g"
            adjusted = max(5, adjusted)

            kcal = food["kcal"] * adjusted / 100.0
            p = food["p"] * adjusted / 100.0
            c = food["c"] * adjusted / 100.0
            f = food["f"] * adjusted / 100.0

            meal_kcal += kcal
            meal_p += p
            meal_c += c
            meal_f += f
            foods_display.append(f"{food['name']}: {adjusted}{unit}")

        if not foods_display:
            continue

        meals.append({
            "meal_name": tpl["meal_name"],
            "time": tpl["time"],
            "foods": foods_display,
            "calories": round(meal_kcal),
            "protein_g": round(meal_p),
            "carbs_g": round(meal_c),
            "fat_g": round(meal_f),
            "tip": tpl["tip"],
        })

    return meals, substitutions


def calc_water_intake_detailed(weight_kg: float, training_days: int, session_minutes: int) -> dict:
    """Nước/ngày = Cân nặng x 0.04 lít + 500ml cho mỗi giờ tập luyện."""
    base = weight_kg * 0.04
    weekly_training_hours = (training_days * session_minutes) / 60.0
    # Phân bổ phần bù nước tập luyện đều cho 7 ngày
    training_bonus_daily = (weekly_training_hours * 0.5) / 7.0
    total = base + training_bonus_daily
    return {
        "base_liters": round(base, 2),
        "training_bonus_liters": round(training_bonus_daily, 2),
        "total_liters": round(total, 2),
        "glasses_250ml": round(total / 0.25),
        "schedule": [
            "300-500ml ngay sau khi thức dậy để bù nước qua đêm.",
            "250-350ml trước khi tập 30 phút.",
            "150-250ml mỗi 15-20 phút trong lúc tập.",
            "500ml trong vòng 1 giờ sau tập để bù điện giải.",
            "Uống rải đều cả ngày, tránh uống ồ ạt một lúc.",
        ],
    }


# --------------------------------------------------------------------------
# PHỤC HỒI
# --------------------------------------------------------------------------
def build_recovery_protocol(
    training_days_per_week: int,
    goal: str,
    age: Optional[int],
    weight_kg: float,
    injuries: Optional[list[str]] = None,
) -> dict:
    """Sinh phác đồ nghỉ ngơi & phục hồi (Trụ cột 3)."""
    injuries = injuries or []

    # Ngày nghỉ: phụ thuộc số buổi tập
    all_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
    if training_days_per_week <= 3:
        training_days = ["Thứ 2", "Thứ 4", "Thứ 6"]
    elif training_days_per_week == 4:
        training_days = ["Thứ 2", "Thứ 3", "Thứ 5", "Thứ 6"]
    elif training_days_per_week == 5:
        training_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6"]
    else:
        training_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"]

    rest_days = [d for d in all_days if d not in training_days]

    sleep_hours = "7.5 - 9 giờ/đêm" if training_days_per_week >= 5 else "7.5 - 8 giờ/đêm"
    if age and age >= 55:
        sleep_hours = "7 - 8 giờ/đêm (ưu tiên chất lượng giấc ngủ hơn số giờ)"

    active_recovery = [
        f"Duy trì 8.000-10.000 bước chân mỗi ngày kể cả ngày nghỉ tập "
        f"để giữ mức tiêu hao năng lượng NEAT.",
        "Giãn cơ tĩnh (Static Stretching) 10 phút sau mỗi buổi tập và trước khi ngủ.",
        "Không tập 2 buổi cùng một nhóm cơ lớn liên tiếp trong vòng 48 giờ.",
        "Foam Rolling (lăn ống bọt) 5-10 phút cho đùi trước, đùi sau và lưng xô "
        "vào ngày nghỉ để giảm đau nhức cơ (DOMS).",
    ]
    if training_days_per_week >= 5:
        active_recovery.append(
            "Cứ 4-6 tuần tập liên tục nên có 1 tuần giảm tải (Deload): "
            "giữ nguyên bài tập nhưng giảm 40-50% khối lượng để đầu hệ thần kinh "
            "trung ương (CNS) hồi phục hoàn toàn."
        )

    # Thực phẩm bổ sung theo mục tiêu
    supplements: list[dict] = [
        {
            "name": "Whey Protein",
            "dose": "20-30g (1 muỗng), 1-2 lần/ngày",
            "when": "Sau tập hoặc bữa phụ khi không kịp ăn đủ đạm",
            "why": "Bổ sung đạm nhanh hấp thu, giúp đạt mục tiêu 1.8-2.2g/kg mà không cần nấu nướng.",
            "priority": "Nên dùng",
        },
        {
            "name": "Creatine Monohydrate",
            "dose": "3-5g/ngày, dùng đều đặn mỗi ngày",
            "when": "Bất kỳ lúc nào trong ngày, kể cả ngày nghỉ",
            "why": "Chất bổ sung có bằng chứng khoa học mạnh nhất về tăng sức mạnh và khối lượng cơ. "
                   "Không cần giai đoạn 'nạp' (loading).",
            "priority": "Nên dùng",
        },
        {
            "name": "Omega-3 (Dầu cá EPA/DHA)",
            "dose": "1-2g EPA+DHA mỗi ngày",
            "when": "Cùng bữa ăn có chất béo",
            "why": "Giảm viêm, hỗ trợ phục hồi khớp và sức khoẻ tim mạch.",
            "priority": "Tùy chọn" if not injuries else "Nên dùng (có chấn thương khớp)",
        },
        {
            "name": "Vitamin D3",
            "dose": "1000-2000 IU/ngày",
            "when": "Cùng bữa ăn có chất béo",
            "why": "Hỗ trợ sức mạnh cơ, miễn dịch và mật độ xương — đặc biệt cần "
                   "cho người ít tiếp xúc ánh nắng.",
            "priority": "Tùy chọn",
        },
        {
            "name": "Điện giải (Electrolytes)",
            "dose": "1 gói pha 500ml-1 lít",
            "when": "Buổi tập trên 60 phút hoặc tập trong môi trường nóng",
            "why": "Bù natri, kali, magie mất qua mồ hôi — giúp giảm chuột rút và mệt lả.",
            "priority": "Tùy chọn",
        },
    ]

    # Cảnh báo quá tải
    overtraining_signs = [
        "Nhịp tim nghỉ (đo lúc mới thức dậy) tăng trên 5 bpm so với bình thường.",
        "Sức mạnh giảm liên tục 2 buổi tập liên tiếp dù đã ăn ngủ đủ.",
        "Mất ngủ, khó ngủ sâu hoặc thức giấc nhiều lần trong đêm.",
        "Đau nhức cơ kéo dài quá 72 giờ sau buổi tập.",
        "Tâm trạng thất thường, mất động lực tập luyện rõ rệt.",
        "Dễ ốm, vết thương lâu lành, chán ăn kéo dài.",
    ]

    return {
        "recommended_sleep_hours": sleep_hours,
        "ideal_bedtime": "22:30 - 23:00",
        "wake_time": "06:00 - 06:30",
        "sleep_protocol": [
            "Ngủ và thức cùng một khung giờ mỗi ngày, kể cả cuối tuần "
            "(ổn định nhịp sinh học giúp tăng chất lượng giấc ngủ sâu).",
            "Khung giờ vàng 22:00-02:00 là giai đoạn cơ thể tiết Hormone tăng trưởng (GH) "
            "mạnh nhất và cortisol xuống thấp nhất — hãy ngủ trước 23:00 để tận dụng.",
            "Ngừng caffeine sau 14:00 (thời gian bán thải của caffeine là 5-6 giờ).",
            "Không dùng điện thoại/màn hình 45-60 phút trước khi ngủ để melatonin "
            "được tiết tự nhiên.",
            "Phòng ngủ tối, mát (20-22°C) và yên tĩnh; nếu tập nặng buổi tối, "
            "nên kết thúc trước khi ngủ 3 giờ.",
            "Ngủ trưa 15-25 phút (nếu có thể) để phục hồi CNS mà không ảnh hưởng giấc đêm.",
        ],
        "rest_days": rest_days,
        "training_days": training_days,
        "active_recovery_tips": active_recovery,
        "neat_target_steps": 8000 if training_days_per_week >= 4 else 9000,
        "supplements": supplements,
        "overtraining_warning_signs": overtraining_signs,
        "stress_management": [
            "Thiền hoặc hít thở sâu 5-10 phút mỗi ngày giúp hạ cortisol.",
            "Đi bộ ngoài trời 20 phút vào buổi sáng để điều hoà nhịp sinh học.",
            "Hạn chế rượu bia — làm giảm mạnh tổng hợp protein cơ bắp trong lúc ngủ.",
        ],
    }


# --------------------------------------------------------------------------
# HÀM TỔNG HỢP
# --------------------------------------------------------------------------
def build_nutrition_plan(
    diagnosis,
    goal: str,
    training_days_per_week: int,
    session_minutes: int,
    allergies: Optional[list[str]] = None,
    age: Optional[int] = None,
    injuries: Optional[list[str]] = None,
) -> dict:
    """Sinh phác đồ dinh dưỡng hoàn chỉnh từ kết quả chẩn đoán."""
    target_cal, adj = calc_target_calories(
        diagnosis.tdee_kcal, goal, diagnosis.body_fat_percentage
    )
    macros = calc_macros(
        target_cal, diagnosis.weight_kg, diagnosis.lean_body_mass_kg,
        goal, diagnosis.body_fat_percentage,
    )
    meals, meal_substitutions = build_meal_plan(
        target_cal, macros, goal, allergies
    )
    water = calc_water_intake_detailed(
        diagnosis.weight_kg, training_days_per_week, session_minutes
    )

    goal_explanation = {
        "cutting": (
            f"Thâm hụt {abs(adj):.0f} kcal/ngày so với TDEE — mức thâm hụt này cho phép "
            f"giảm mỡ đều đặn mà vẫn giữ được cơ và không làm tụt hormone."
        ),
        "bulking": (
            f"Thặng dư {adj:.0f} kcal/ngày so với TDEE — mức tăng nhẹ (lean bulk) giúp "
            f"tối đa hoá tăng cơ và hạn chế tích mỡ."
        ),
        "recomp": (
            f"Thâm hụt rất nhẹ {abs(adj):.0f} kcal/ngày so với TDEE — đủ để giảm mỡ "
            f"từ từ trong khi nạp đủ năng lượng cho việc xây cơ."
        ),
        "endurance": (
            "Ăn ngang mức TDEE để duy trì cân nặng và tối ưu năng lượng cho các buổi tập "
            "cường độ cao."
        ),
    }.get(goal, "")

    return {
        "target_daily_calories": int(target_cal),
        "caloric_adjustment": int(adj),
        "tdee_kcal": diagnosis.tdee_kcal,
        "bmr_kcal": diagnosis.bmr_kcal,
        "caloric_strategy": goal_explanation,
        "macros": macros,
        "macro_guidance": {
            "protein": (
                f"{macros['protein_grams']}g/ngày = {macros['protein_per_kg']}g/kg cân nặng "
                f"({macros['protein_per_kg_lbm']}g/kg khối lượng cơ nạc). Chia đều 4-5 bữa, "
                f"mỗi bữa 30-45g đạm để tối ưu tổng hợp protein cơ bắp."
            ),
            "fat": (
                f"{macros['fat_grams']}g/ngày ({macros['fat_percent']}% tổng calo). "
                f"Ưu tiên chất béo tốt: dầu oliu, quả bơ, cá béo, các loại hạt. "
                f"Không xuống dưới 0.6g/kg vì sẽ ảnh hưởng hormone testosterone."
            ),
            "carbs": (
                f"{macros['carbs_grams']}g/ngày ({macros['carbs_percent']}% tổng calo). "
                f"Ưu tiên tinh bột phức (gạo lứt, khoai lang, yến mạch) và dồn nhiều hơn "
                f"vào bữa trước/sau tập để nạp glycogen cho cơ."
            ),
        },
        "sample_meals": meals,
        "meal_substitutions": meal_substitutions,
        "daily_water_liters": water["total_liters"],
        "water_plan": water,
        "eating_rules": [
            "Ăn đủ 4-5 bữa/ngày, không bỏ bữa sáng — bỏ bữa sáng làm tăng cảm giác thèm ăn "
            "và dễ ăn quá mức vào buổi tối.",
            "Đạm là ưu tiên số 1: nếu chỉ theo dõi được một chỉ số, hãy theo dõi lượng đạm.",
            "Rau xanh tối thiểu 300-400g/ngày để đủ chất xơ và vi chất.",
            "Uống nước trước bữa ăn 20 phút giúp kiểm soát cảm giác đói hiệu quả.",
            "Nấu ăn tại nhà ít nhất 5 bữa/tuần — kiểm soát được dầu mỡ và gia vị tốt hơn nhiều.",
            "Nếu ăn ngoài: chọn món hấp/luộc/nướng, xin ít dầu, gọi thêm rau và bỏ da thịt.",
            "Cho phép 1 bữa ăn tự do (cheat meal) mỗi 7-10 ngày — điều này giúp duy trì "
            "tâm lý thoải mái và không phá vỡ kết quả nếu các bữa còn lại tuân thủ.",
            "Chuẩn bị thức ăn trước (meal prep) cho 2-3 ngày để tránh quyết định vội vàng khi đói.",
        ],
        "foods_to_prioritize": [
            "Đạm: ức gà, thịt bò nạc, cá hồi/cá basa, trứng, tôm, sữa chua Hy Lạp.",
            "Tinh bột phức: gạo lứt, khoai lang, yến mạch, bún, bánh mì nguyên cám.",
            "Chất béo tốt: quả bơ, dầu oliu, hạnh nhân, hạt điều, mè.",
            "Rau củ: bông cải xanh, rau muống, xà lách, cà chua, dưa leo.",
            "Trái cây: chuối (trước/sau tập), táo, cam, việt quất.",
        ],
        "foods_to_limit": [
            "Nước ngọt có ga và trà sữa (calo rỗng, không tạo cảm giác no).",
            "Đồ chiên rán nhiều dầu, thức ăn nhanh.",
            "Rượu bia (làm giảm tổng hợp protein cơ bắp và phá vỡ giấc ngủ sâu).",
            "Bánh kẹo ngọt, snack đóng gói.",
            "Thịt chế biến sẵn (xúc xích, thịt xông khói) — nhiều natri và chất bảo quản.",
        ],
        "recovery_plan": build_recovery_protocol(
            training_days_per_week, goal, age, diagnosis.weight_kg, injuries
        ),
    }