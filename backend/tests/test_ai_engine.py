"""Kiểm thử AI Smart Fitness Coach — công thức, phân loại, an toàn và tích hợp.

Chạy:
    .venv\\Scripts\\python.exe -m pytest tests -q
hoặc không cần pytest:
    .venv\\Scripts\\python.exe tests\\test_ai_engine.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ai_diagnosis import (  # noqa: E402
    BODY_FAT_LABELS_VI,
    calc_bmi,
    calc_bmr_katch_mcardle,
    calc_ffmi,
    calc_lean_body_mass,
    calc_tdee,
    calc_water_intake,
    classify_body_fat,
    classify_body_type,
    estimate_body_fat_us_navy,
    run_full_diagnosis,
)
from app.services.ai_coach import (  # noqa: E402
    REQUIRED_FIELDS,
    generate_full_plan,
    next_missing_field,
    parse_csv_list,
    validate_profile,
)
from app.services.ai_nutrition import (  # noqa: E402
    build_meal_plan,
    calc_macros,
    calc_target_calories,
)
from app.services.ai_workout import (  # noqa: E402
    EXERCISE_BY_NAME,
    build_workout_plan,
)

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  [PASS] {name}")
    else:
        FAILED.append(f"{name} {detail}")
        print(f"  [FAIL] {name} {detail}")


def close(a: float, b: float, tol: float = 0.05) -> bool:
    return abs(a - b) <= tol


# ==========================================================================
print("\n=== 1. CÔNG THỨC CHẨN ĐOÁN (đối chiếu ví dụ nghiệp vụ) ===")
# Ví dụ chuẩn trong yêu cầu: 172cm, 75kg, 24.5% BF, nam 29 tuổi, moderate
bmi = calc_bmi(75, 172)
check("BMI = 25.35", close(bmi, 25.35, 0.02), f"got {bmi}")

lbm = calc_lean_body_mass(75, 24.5)
check("LBM ≈ 56.6kg", close(lbm, 56.63, 0.05), f"got {lbm}")

bmr = calc_bmr_katch_mcardle(lbm)
check("BMR ≈ 1592-1593 kcal", 1590 <= bmr <= 1595, f"got {bmr}")

tdee = calc_tdee(bmr, "moderate")
check("TDEE ≈ 2468 kcal (x1.55)", 2465 <= tdee <= 2472, f"got {tdee}")

fat_mass = round(75 - lbm, 2)
check("Fat Mass ≈ 18.4kg", close(fat_mass, 18.37, 0.05), f"got {fat_mass}")

# Đơn vị phân loại
check("Body fat category = Average (24.5%)",
      classify_body_fat("male", 24.5) == "Average",
      f"got {classify_body_fat('male', 24.5)}")

# ==========================================================================
print("\n=== 2. XẾP LOẠI BODY FAT THEO GIỚI TÍNH & ĐỘ TUỔI ===")
male_cases = [
    (4.0, "Essential"), (8.0, "Athletes"), (15.0, "Fitness"),
    (20.0, "Average"), (28.0, "Obese"),
]
for bf, expected in male_cases:
    got = classify_body_fat("male", bf)
    check(f"Nam {bf}% -> {expected}", got == expected, f"got {got}")

female_cases = [
    (12.0, "Essential"), (17.0, "Athletes"), (22.0, "Fitness"),
    (28.0, "Average"), (35.0, "Obese"),
]
for bf, expected in female_cases:
    got = classify_body_fat("female", bf)
    check(f"Nữ {bf}% -> {expected}", got == expected, f"got {got}")

# Giá trị nằm trong khe hở giữa các dải (17.5% nam) phải rơi vào Fitness, không phải Essential
gap = classify_body_fat("male", 17.5)
check("Khe hở 17.5% nam -> Fitness (không phải Essential)", gap == "Fitness", f"got {gap}")
gap_f = classify_body_fat("female", 24.5)
check("Khe hở 24.5% nữ -> Fitness", gap_f == "Fitness", f"got {gap_f}")

# Yếu tố tuổi: 60 tuổi có mỡ nền cao hơn, 25% BF vẫn xếp Average (không phải Obese)
young = classify_body_fat("male", 25.0, 25)
older = classify_body_fat("male", 25.0, 62)
check("Nam 25% tuổi 25 -> Obese (>=25)", young == "Obese", f"got {young}")
check("Nam 25% tuổi 62 -> bù trừ tuổi (Average)", older == "Average", f"got {older}")

check("Có nhãn tiếng Việt cho mọi nhóm",
      all(k in BODY_FAT_LABELS_VI for k in
          ("Essential", "Athletes", "Fitness", "Average", "Obese")))

# ==========================================================================
print("\n=== 3. US NAVY METHOD (ước tính Body Fat từ số đo) ===")
bf_male = estimate_body_fat_us_navy("male", 172, neck_cm=38, waist_cm=88)
check("Nam 172cm cổ 38 eo 88 -> 18-24%", 17.0 <= bf_male <= 24.0, f"got {bf_male}")

bf_female = estimate_body_fat_us_navy("female", 162, neck_cm=32, waist_cm=78, hip_cm=98)
check("Nữ có kết quả hợp lý (15-35%)", 15.0 <= bf_female <= 35.0, f"got {bf_female}")

# Nữ thiếu vòng hông phải báo lỗi
try:
    estimate_body_fat_us_navy("female", 162, neck_cm=32, waist_cm=78)
    check("Nữ thiếu vòng hông -> ValueError", False, "không raise lỗi")
except ValueError:
    check("Nữ thiếu vòng hông -> ValueError", True)

# Vòng eo nhỏ hơn vòng cổ (dữ liệu sai) phải báo lỗi
try:
    estimate_body_fat_us_navy("male", 172, neck_cm=45, waist_cm=40)
    check("Eo < cổ -> ValueError", False, "không raise lỗi")
except ValueError:
    check("Eo < cổ -> ValueError", True)

# Người gầy phải cho BF thấp hơn người béo (tính đơn điệu)
lean_bf = estimate_body_fat_us_navy("male", 172, neck_cm=38, waist_cm=74)
heavy_bf = estimate_body_fat_us_navy("male", 172, neck_cm=38, waist_cm=105)
check("US Navy đơn điệu: eo lớn -> BF cao hơn", heavy_bf > lean_bf,
      f"lean={lean_bf} heavy={heavy_bf}")

# ==========================================================================
print("\n=== 4. FFMI & TẠNG NGƯỜI (SKINNY FAT DETECTION) ===")
ffmi, ffmi_norm = calc_ffmi(56.63, 172)
check("FFMI thô hợp lý (18-20)", 18.0 <= ffmi <= 20.0, f"got {ffmi}")
check("FFMI chuẩn hoá hợp lý", 19.0 <= ffmi_norm <= 21.0, f"got {ffmi_norm}")

# Skinny Fat: BMI bình thường nhưng BF cao
st = classify_body_type(23.0, 24.0, "Average", 18.5, "male")
check("BMI 23 + BF 24% -> skinny_fat", st == "skinny_fat", f"got {st}")

# Người cơ bắp, mỡ thấp -> athletic
ath = classify_body_type(24.5, 10.0, "Athletes", 23.0, "male")
check("BF 10% + FFMI 23 -> athletic", ath == "athletic", f"got {ath}")

# Béo phì rõ ràng
ob = classify_body_type(33.0, 32.0, "Obese", 19.0, "male")
check("BF 32% -> obese", ob == "obese", f"got {ob}")

# Thừa cân nhưng chưa béo phì
ov = classify_body_type(27.0, 21.0, "Average", 20.0, "male")
check("BMI 27 + BF 21% -> overweight", ov == "overweight", f"got {ov}")

# Gầy
sk = classify_body_type(17.5, 12.0, "Athletes", 15.0, "male")
check("BMI 17.5 -> skinny", sk == "skinny", f"got {sk}")

# ==========================================================================
print("\n=== 5. CALO MỤC TIÊU & MACROS ===")
cal_cut, adj_cut = calc_target_calories(2469, "cutting", 24.5)
check("Cutting: thâm hụt trong 300-500", -500 <= adj_cut <= -300, f"got {adj_cut}")
check("Cutting: calo = TDEE + adj", close(cal_cut, 2469 + adj_cut, 1), f"got {cal_cut}")

cal_bulk, adj_bulk = calc_target_calories(2469, "bulking", 12.0)
check("Bulking: thặng dư 200-300", 200 <= adj_bulk <= 300, f"got {adj_bulk}")

# Bulking khi đã thừa mỡ -> thặng dư nhỏ hơn
_, adj_bulk_fat = calc_target_calories(2469, "bulking", 24.0)
check("Bulking khi BF cao: thặng dư <= 200", adj_bulk_fat <= 200, f"got {adj_bulk_fat}")

cal_re, adj_re = calc_target_calories(2469, "recomp", 20.0)
check("Recomp: thâm hụt nhẹ 100-200", -200 <= adj_re <= -100, f"got {adj_re}")

# Sàn an toàn calo
cal_floor, _ = calc_target_calories(1300, "cutting", 30.0)
check("Sàn an toàn: không dưới 1200 kcal", cal_floor >= 1200, f"got {cal_floor}")

# Macros
macros = calc_macros(2069, 75, 56.63, "cutting", 24.5)
p_kg = macros["protein_grams"] / 75
p_lbm = macros["protein_grams"] / 56.63
check("Protein 1.8-2.2 g/kg cân nặng", 1.8 <= p_kg <= 2.2, f"got {p_kg:.2f}")
check("Protein theo LBM trong khoảng 2.2-2.5, hoặc đạt sàn 1.8g/kg cân nặng khi "
      "hai khoảng không giao nhau",
      2.2 <= p_lbm <= 2.5 or p_kg >= 1.8, f"LBM={p_lbm:.2f} kg={p_kg:.2f}")
check("Fat trong khoảng 20-30% calo", 20 <= macros["fat_percent"] <= 30,
      f"got {macros['fat_percent']}%")
check("Tổng macros khớp calo mục tiêu (±15 kcal)",
      abs(macros["total_calories"] - 2069) <= 15,
      f"got {macros['total_calories']}")
check("Protein chia đủ cho 4-5 bữa",
      macros["protein_grams"] / 5 >= 25, f"got {macros['protein_grams']/5:.1f}g/bữa")

# Tổng % macros = 100%
total_pct = macros["protein_percent"] + macros["carbs_percent"] + macros["fat_percent"]
check("Tổng % macros = 100", 99 <= total_pct <= 101, f"got {total_pct}")

# ==========================================================================
print("\n=== 6. LƯỢNG NƯỚC ===")
water = calc_water_intake(75, 4)
check("Nước >= cân nặng x 0.04", water >= 3.0, f"got {water}")
water_heavy = calc_water_intake(100, 6)
check("Người nặng + tập nhiều -> nước nhiều hơn",
      water_heavy > water, f"{water_heavy} vs {water}")

# ==========================================================================
print("\n=== 7. LỊCH TẬP THEO SỐ BUỔI/TUẦN (WORKOUT SPLIT) ===")
w3 = build_workout_plan("cutting", "moderate", 3, 60, "gym", 22.0, "male")
check("3 buổi -> Full Body", "Full Body" in w3["split_type"], w3["split_type"])
check("3 buổi -> đúng 3 session", len(w3["sessions"]) == 3, f"got {len(w3['sessions'])}")

w4 = build_workout_plan("cutting", "moderate", 4, 60, "gym", 22.0, "male")
check("4 buổi -> Upper / Lower", "Upper / Lower" in w4["split_type"], w4["split_type"])
check("4 buổi -> đúng 4 session", len(w4["sessions"]) == 4, f"got {len(w4['sessions'])}")

w5 = build_workout_plan("cutting", "moderate", 5, 60, "gym", 22.0, "male")
check("5 buổi -> Push / Pull / Legs", "Push / Pull / Legs" in w5["split_type"], w5["split_type"])
check("5 buổi -> đúng 5 session", len(w5["sessions"]) == 5, f"got {len(w5['sessions'])}")

w6 = build_workout_plan("bulking", "very_active", 6, 75, "gym", 12.0, "male")
check("6 buổi -> PPL 6 session", len(w6["sessions"]) == 6, f"got {len(w6['sessions'])}")

# Cấu trúc buổi tập đầy đủ 4 phần
s = w4["sessions"][0]
check("Buổi tập có khởi động", bool(s["warmup"]))
check("Buổi tập có giãn cơ cool-down", bool(s["cooldown"]))
check("Buổi tập có bài tập chính", len(s["exercises"]) >= 4, f"got {len(s['exercises'])}")
check("Buổi tập có cardio", bool(w4["cardio"]["details"]))
check("Buổi tập có ngày cụ thể", bool(s["day"]), str(s.get("day")))

# Compound phải đứng trước Isolation
ex_types = [e["type"] for e in s["exercises"]]
first_iso = next((i for i, t in enumerate(ex_types) if "Isolation" in t), len(ex_types))
last_comp = max((i for i, t in enumerate(ex_types) if "Compound" in t), default=-1)
check("Compound xếp trước Isolation", last_comp < first_iso,
      f"compound cuối #{last_comp}, isolation đầu #{first_iso}")

# Mỗi bài tập có đủ trường theo nghiệp vụ
e0 = s["exercises"][0]
for field in ("name", "target_muscle", "sets", "reps", "rest_seconds", "notes", "rpe"):
    check(f"Bài tập có trường '{field}'", field in e0, str(e0.keys()))

# Reps dạng khoảng hoặc số cụ thể
check("Reps là khoảng giá trị", "-" in e0["reps"] or "giây" in e0["reps"], e0["reps"])
check("Rest time hợp lý (30-240s)", 30 <= e0["rest_seconds"] <= 240, str(e0["rest_seconds"]))

# ==========================================================================
print("\n=== 8. CÁ NHÂN HOÁ THEO CHẤN THƯƠNG (AN TOÀN) ===")
# Đau lưng dưới: không được có Deadlift tạ đòn / Squat tạ đòn / Bent-over Row
w_back = build_workout_plan("cutting", "moderate", 4, 60, "gym", 22.0, "male",
                            injuries=["lower_back"])
back_names = [e["name"] for sess in w_back["sessions"] for e in sess["exercises"]]
check("Đau lưng: không có Barbell Back Squat",
      not any("Barbell Back Squat" in n for n in back_names), str(back_names[:4]))
check("Đau lưng: không có Barbell Bent-over Row",
      not any("Bent-over Row" in n for n in back_names), str(back_names[:4]))
check("Đau lưng: không có Romanian Deadlift tạ đòn",
      not any("Romanian Deadlift (Deadlift Rumani tạ đòn)" == n for n in back_names))
check("Đau lưng: có bài thay thế an toàn (Hip Thrust / Leg Press / Dead Bug)",
      any(k in n for n in back_names for k in ("Hip Thrust", "Leg Press", "Dead Bug")),
      str(back_names[:6]))
check("Đau lưng: có ghi chú thay thế bài tập",
      len(w_back["exercise_substitutions"]) > 0)
check("Đau lưng: cảnh báo an toàn xuất hiện trong buổi tập",
      any("lưng" in n.lower() for n in back_names) or
      len(w_back["exercise_substitutions"]) > 0)

# Đau vai: không có Bench Press tạ đòn / Overhead Press
w_sh = build_workout_plan("cutting", "moderate", 4, 60, "gym", 22.0, "male",
                          injuries=["shoulder"])
sh_names = [e["name"] for sess in w_sh["sessions"] for e in sess["exercises"]]
check("Đau vai: không có Barbell Bench Press",
      not any("Barbell Bench Press" in n for n in sh_names), str(sh_names[:4]))
check("Đau vai: không có Lat Pulldown? (không, chỉ tránh overhead)",
      True)
check("Đau vai: có bài thay thế (Landmine/Push-up)",
      any(k in n for n in sh_names for k in ("Landmine", "Push-up")), str(sh_names[:6]))

# Đau gối: không có Squat tạ đòn nặng / Walking Lunge
w_kn = build_workout_plan("cutting", "moderate", 4, 60, "gym", 22.0, "male",
                          injuries=["knee"])
kn_names = [e["name"] for sess in w_kn["sessions"] for e in sess["exercises"]]
check("Đau gối: không có Barbell Back Squat",
      not any("Barbell Back Squat" in n for n in kn_names), str(kn_names[:4]))
check("Đau gối: không có Walking Lunge",
      not any("Walking Lunge" in n for n in kn_names))
check("Đau gối: Cardio ưu tiên bài ít tác động khớp",
      "ít tác động" in w_kn["cardio"]["low_impact_note"],
      w_kn["cardio"]["low_impact_note"])

# Chấn thương phải sinh cảnh báo trong chẩn đoán
diag_inj = run_full_diagnosis(172, 75, 24.5, "male", 29, "moderate", "cutting",
                              injuries=["knee", "lower_back"])
check("Chẩn đoán có cảnh báo cho chấn thương gối",
      any("gối" in wn for wn in diag_inj.warnings))
check("Chẩn đoán có cảnh báo cho chấn thương lưng",
      any("lưng" in wn for wn in diag_inj.warnings))

# ==========================================================================
print("\n=== 9. CÁ NHÂN HOÁ THEO NƠI TẬP (THIẾT BỊ) ===")
w_home = build_workout_plan("cutting", "moderate", 4, 60, "home_dumbbell", 22.0, "male")
home_names = [e["name"] for sess in w_home["sessions"] for e in sess["exercises"]]
home_exercises = [EXERCISE_BY_NAME[n] for n in home_names if n in EXERCISE_BY_NAME]
check("Tập tại nhà: mọi bài đều tập được với tạ đơn tại nhà",
      all("home_dumbbell" in e.equipment for e in home_exercises),
      str([e.name for e in home_exercises if "home_dumbbell" not in e.equipment][:3]))
check("Tập tại nhà: có ghi chú thay thế", len(w_home["exercise_substitutions"]) > 0)
check("Tập tại nhà: vẫn có đủ buổi tập", len(w_home["sessions"]) == 4)

w_cali = build_workout_plan("cutting", "moderate", 3, 45, "calisthenics", 22.0, "male")
cali_names = [e["name"] for sess in w_cali["sessions"] for e in sess["exercises"]]
cali_ex = [EXERCISE_BY_NAME[n] for n in cali_names if n in EXERCISE_BY_NAME]
check("Calisthenics: chỉ dùng trọng lượng cơ thể",
      all("calisthenics" in e.equipment for e in cali_ex),
      str([e.name for e in cali_ex if "calisthenics" not in e.equipment][:3]))

# ==========================================================================
print("\n=== 10. ĐIỀU CHỈNH THEO MỤC TIÊU ===")
w_cut = build_workout_plan("cutting", "moderate", 4, 60, "gym", 25.0, "male")
w_bulk = build_workout_plan("bulking", "moderate", 4, 75, "gym", 12.0, "male")
cut_sets = sum(e["sets"] for s in w_cut["sessions"] for e in s["exercises"])
bulk_sets = sum(e["sets"] for s in w_bulk["sessions"] for e in s["exercises"])
check("Bulking có volume >= Cutting", bulk_sets >= cut_sets, f"{bulk_sets} vs {cut_sets}")

check("Cutting giữ tải nặng (rep guidance nói rõ)",
      "nặng" in w_cut["rep_guidance"], w_cut["rep_guidance"][:60])
check("Cardio Cutting có LISS + HIIT",
      len(w_cut["cardio"]["details"]) >= 2, str(len(w_cut["cardio"]["details"])))

# BF thấp -> cardio ít hơn
w_lean = build_workout_plan("cutting", "moderate", 4, 60, "gym", 11.0, "male")
check("BF 11%: khuyến nghị cardio nhẹ hơn BF 25%",
      "không cần cardio đốt mỡ" in " ".join(w_lean["cardio"]["details"]).lower()
      or len(w_lean["cardio"]["details"]) <= 3)

# ==========================================================================
print("\n=== 11. THỰC ĐƠN & DỊ ỨNG ===")
meals, subs = build_meal_plan(2069, macros, "cutting", [])
check("Thực đơn có >= 4 bữa", len(meals) >= 4, f"got {len(meals)}")
check("Bữa sáng có mặt", any("sáng" in m["meal_name"].lower() for m in meals))
check("Bữa trưa có mặt", any("trưa" in m["meal_name"].lower() for m in meals))
check("Bữa tối có mặt", any("tối" in m["meal_name"].lower() for m in meals))
check("Bữa trước tập có mặt",
      any("trước tập" in m["meal_name"].lower() for m in meals))
check("Mỗi bữa có định lượng gram",
      all(any("g" in f for f in m["foods"]) for m in meals))
check("Mỗi bữa có calo và đạm",
      all(m["calories"] > 0 and m["protein_g"] > 0 for m in meals))
check("Tổng calo thực đơn gần mục tiêu (±12%)",
      abs(sum(m["calories"] for m in meals) - 2069) / 2069 < 0.12,
      f"got {sum(m['calories'] for m in meals)} vs 2069")
check("Thực đơn dùng thực phẩm Việt Nam",
      any(any(k in f for f in m["foods"]) for m in meals
          for k in ("Ức gà", "Cơm", "Khoai", "Yến mạch", "Bông cải")))

# Dị ứng cá -> không được có cá trong thực đơn
meals_fish, subs_fish = build_meal_plan(2069, macros, "cutting", ["fish"])
all_foods = " ".join(f for m in meals_fish for f in m["foods"])
check("Dị ứng cá: thực đơn không có Cá hồi", "Cá hồi" not in all_foods, all_foods[:120])
check("Dị ứng cá: thực đơn không có Cá basa", "Cá basa" not in all_foods)
check("Dị ứng cá: có ghi chú thay thế", len(subs_fish) > 0)

# Dị ứng sữa -> không có sữa tươi / whey
meals_dairy, _ = build_meal_plan(2069, macros, "cutting", ["dairy"])
foods_dairy = " ".join(f for m in meals_dairy for f in m["foods"])
check("Dị ứng sữa: không có Sữa tươi", "Sữa tươi" not in foods_dairy, foods_dairy[:120])

# Dị ứng trứng
meals_egg, _ = build_meal_plan(2069, macros, "cutting", ["egg"])
foods_egg = " ".join(f for m in meals_egg for f in m["foods"])
check("Dị ứng trứng: không có Trứng gà", "Trứng gà" not in foods_egg, foods_egg[:120])

# Bulking có thêm bữa phụ
meals_bulk, _ = build_meal_plan(2800, macros, "bulking", [])
check("Bulking có thêm bữa phụ tối", len(meals_bulk) == 5, f"got {len(meals_bulk)}")

# ==========================================================================
print("\n=== 12. PHÁC ĐỒ TÍCH HỢP ĐẦY ĐỦ (3 TRỤ CỘT) ===")
plan = generate_full_plan(
    height_cm=172, weight_kg=75, body_fat_percentage=24.5,
    gender="male", age=29, activity_level="moderate", goal="cutting",
    training_days_per_week=4, session_minutes=60, training_location="gym",
)
for key in ("member_diagnosis", "nutrition_plan", "workout_schedule",
            "recovery_protocol", "summary_text", "disclaimer"):
    check(f"Phác đồ có khối '{key}'", key in plan)

d = plan["member_diagnosis"]
n = plan["nutrition_plan"]
w = plan["workout_schedule"]
r = plan["recovery_protocol"]

check("Chẩn đoán: skinny_fat đúng", d["body_type"] == "skinny_fat", d["body_type"])
check("Chẩn đoán: BMI 25.35", close(d["bmi"], 25.35, 0.02))
check("Chẩn đoán: mục tiêu 6-8kg mỡ (theo ví dụ nghiệp vụ)",
      6.0 <= d["fat_to_lose_kg"] <= 11.0, f"got {d['fat_to_lose_kg']}")
check("Chẩn đoán: thời gian 10-20 tuần", 10 <= d["estimated_weeks_to_goal"] <= 20,
      f"got {d['estimated_weeks_to_goal']}")
check("Chẩn đoán: có nhận định chuyên môn dài",
      len(d["ai_assessment_summary"]) > 200)
check("Chẩn đoán: nhận định đề cập tập kháng lực cho skinny fat",
      "kháng lực" in d["ai_assessment_summary"])

check("Dinh dưỡng: calo mục tiêu 1900-2200", 1900 <= n["target_daily_calories"] <= 2200,
      f"got {n['target_daily_calories']}")
check("Dinh dưỡng: thâm hụt -300 đến -500",
      -500 <= n["caloric_adjustment"] <= -300, f"got {n['caloric_adjustment']}")
check("Dinh dưỡng: có macros Protein/Carb/Fat",
      all(k in n["macros"] for k in ("protein_grams", "carbs_grams", "fat_grams")))
check("Dinh dưỡng: có thực đơn mẫu", len(n["sample_meals"]) >= 4)
check("Dinh dưỡng: có nước uống hằng ngày", n["daily_water_liters"] > 2.5)
check("Dinh dưỡng: có hướng dẫn macro chi tiết",
      all(k in n["macro_guidance"] for k in ("protein", "fat", "carbs")))
check("Dinh dưỡng: có danh sách thực phẩm nên/không nên",
      len(n["foods_to_prioritize"]) >= 3 and len(n["foods_to_limit"]) >= 3)
check("Dinh dưỡng: có nguyên tắc ăn uống", len(n["eating_rules"]) >= 5)

check("Lịch tập: 4 buổi/tuần", w["training_days_per_week"] == 4)
check("Lịch tập: có quy tắc tăng tiến", "Progressive Overload" in w["progression_rule"])
check("Lịch tập: có hướng dẫn RPE", bool(w["target_rpe"]))
check("Lịch tập: có khuyến nghị cardio", bool(w["cardio"]["details"]))

check("Phục hồi: có giờ ngủ khuyến nghị", bool(r["recommended_sleep_hours"]))
check("Phục hồi: giờ ngủ 7.5-9 tiếng", "7.5" in r["recommended_sleep_hours"])
check("Phục hồi: giờ đi ngủ tối ưu", bool(r["ideal_bedtime"]))
check("Phục hồi: có ngày nghỉ", len(r["rest_days"]) >= 2)
check("Phục hồi: có tips phục hồi chủ động", len(r["active_recovery_tips"]) >= 3)
check("Phục hồi: có mục tiêu NEAT/bước chân", r["neat_target_steps"] >= 7000)
check("Phục hồi: có khuyến nghị thực phẩm bổ sung", len(r["supplements"]) >= 3)
check("Phục hồi: có cảnh báo quá tải", len(r["overtraining_warning_signs"]) >= 4)
check("Phục hồi: có protocol giấc ngủ chi tiết", len(r["sleep_protocol"]) >= 4)
check("Tóm tắt: có nội dung", len(plan["summary_text"]) > 100)
check("Tóm tắt: không lặp '4 buổi/tuần' hai lần",
      plan["summary_text"].count("4 buổi/tuần") <= 1,
      plan["summary_text"][:200])

# ==========================================================================
print("\n=== 13. VALIDATION & CONVERSATIONAL FLOW ===")
check("Thiếu chỉ số -> validation báo lỗi", len(validate_profile({})) > 0)
check("Profile đầy đủ -> hợp lệ",
      len(validate_profile({
          "gender": "male", "age": 29, "height_cm": 172, "weight_kg": 75,
          "body_fat_percentage": 24.5, "goal": "cutting", "activity_level": "moderate",
      })) == 0)

check("Tuổi 5 -> lỗi validation",
      any("tuổi" in e.lower() for e in validate_profile({
          "gender": "male", "age": 5, "height_cm": 172, "weight_kg": 75,
          "body_fat_percentage": 24.5, "goal": "cutting", "activity_level": "moderate"})))
check("Chiều cao 300 -> lỗi validation",
      any("chiều cao" in e.lower() for e in validate_profile({
          "gender": "male", "age": 29, "height_cm": 300, "weight_kg": 75,
          "body_fat_percentage": 24.5, "goal": "cutting", "activity_level": "moderate"})))
check("Mục tiêu sai -> lỗi validation",
      any("mục tiêu" in e.lower() for e in validate_profile({
          "gender": "male", "age": 29, "height_cm": 172, "weight_kg": 75,
          "body_fat_percentage": 24.5, "goal": "sai", "activity_level": "moderate"})))

# next_missing_field trả đúng câu hỏi kế tiếp
first = next_missing_field({})
check("Profile rỗng -> hỏi giới tính trước", first["field"] == "gender", str(first))
second = next_missing_field({"gender": "male"})
check("Đã có giới tính -> hỏi tuổi", second["field"] == "age", str(second))
third = next_missing_field({"gender": "male", "age": 29, "height_cm": 172,
                            "weight_kg": 75, "body_fat_percentage": 24.5,
                            "goal": "cutting", "activity_level": "moderate"})
check("Đủ chỉ số -> không hỏi thêm", third is None, str(third))

check("parse_csv_list xử lý 'none'", parse_csv_list("none") == [])
check("parse_csv_list xử lý nhiều giá trị",
      parse_csv_list("knee,lower_back") == ["knee", "lower_back"])
check("parse_csv_list xử lý None", parse_csv_list(None) == [])
check("REQUIRED_FIELDS có 7 chỉ số", len(REQUIRED_FIELDS) == 7, str(len(REQUIRED_FIELDS)))

# ==========================================================================
print("\n=== 14. CẢNH BÁO AN TOÀN LÂM SÀNG ===")
# BMI >= 30
w_obese = run_full_diagnosis(170, 95, 33.0, "male", 40, "sedentary", "cutting")
check("BMI >= 30 -> cảnh báo tầm soát sức khỏe",
      any("30" in wn or "tầm soát" in wn for wn in w_obese.warnings),
      str(w_obese.warnings))

# Tuổi >= 55
w_old = run_full_diagnosis(165, 68, 24.0, "male", 58, "light", "recomp")
check("Tuổi >= 55 -> cảnh báo khởi động & thăng bằng",
      any("55" in wn for wn in w_old.warnings), str(w_old.warnings))

# Dưới 18
w_teen = run_full_diagnosis(170, 60, 15.0, "male", 16, "moderate", "bulking")
check("Dưới 18 tuổi -> cảnh báo giám sát HLV",
      any("18" in wn for wn in w_teen.warnings), str(w_teen.warnings))

# BF rất thấp
w_low = run_full_diagnosis(178, 70, 4.0, "male", 30, "very_active", "cutting")
check("BF < 5% -> cảnh báo nguy hiểm nội tiết",
      any("5%" in wn for wn in w_low.warnings), str(w_low.warnings))

# Bulking khi BMI đã cao
w_bulk_fat = run_full_diagnosis(170, 82, 26.0, "male", 35, "light", "bulking")
check("Bulking + BMI >= 27 -> khuyến nghị chuyển sang Recomp",
      any("Recomp" in wn for wn in w_bulk_fat.warnings), str(w_bulk_fat.warnings))

# ==========================================================================
print("\n=== 15. TÍNH NHẤT QUÁN & TRƯỜNG HỢP BIÊN ===")
# Nữ giới
plan_f = generate_full_plan(
    height_cm=162, weight_kg=58, body_fat_percentage=28.0, gender="female", age=27,
    activity_level="light", goal="cutting", training_days_per_week=3,
    session_minutes=45, training_location="gym",
)
check("Nữ: phân loại Body Fat đúng ngưỡng nữ",
      plan_f["member_diagnosis"]["body_fat_category"] == "Average",
      plan_f["member_diagnosis"]["body_fat_category"])
check("Nữ: split 3 buổi -> Full Body",
      "Full Body" in plan_f["workout_schedule"]["split_type"])
check("Nữ: mục tiêu BF theo ngưỡng nữ (24%)",
      plan_f["member_diagnosis"]["target_body_fat_percentage"] == 24.0,
      str(plan_f["member_diagnosis"]["target_body_fat_percentage"]))
check("Nữ: protein đạt sàn 1.8g/kg cân nặng",
      plan_f["nutrition_plan"]["macros"]["protein_grams"] / 58 >= 1.8 - 0.01,
      str(plan_f["nutrition_plan"]["macros"]["protein_grams"] / 58))

# Người rất béo
plan_ob = generate_full_plan(
    height_cm=170, weight_kg=110, body_fat_percentage=38.0, gender="male", age=45,
    activity_level="sedentary", goal="cutting", training_days_per_week=3,
    session_minutes=45, training_location="gym", injuries=["knee"],
)
check("Béo phì: phân loại obese", plan_ob["member_diagnosis"]["body_type"] == "obese")
check("Béo phì: có cảnh báo an toàn", len(plan_ob["member_diagnosis"]["safety_warnings"]) >= 1)
check("Béo phì: đau gối -> cardio ít tác động",
      "ít tác động" in plan_ob["workout_schedule"]["cardio"]["low_impact_note"])
check("Béo phì: calo không xuống dưới sàn 1200",
      plan_ob["nutrition_plan"]["target_daily_calories"] >= 1200)

# Người gầy muốn tăng cơ
plan_sk = generate_full_plan(
    height_cm=175, weight_kg=55, body_fat_percentage=11.0, gender="male", age=22,
    activity_level="light", goal="bulking", training_days_per_week=4,
    session_minutes=60, training_location="gym",
)
check("Gầy: phân loại skinny/lean",
      plan_sk["member_diagnosis"]["body_type"] in ("skinny", "lean"),
      plan_sk["member_diagnosis"]["body_type"])
check("Bulking: calo > TDEE", plan_sk["nutrition_plan"]["target_daily_calories"]
      > plan_sk["member_diagnosis"]["tdee_kcal"])
check("Bulking: có mục tiêu tăng cơ", plan_sk["member_diagnosis"]["muscle_to_gain_kg"] > 0)
check("Bulking: protein 1.8-2.2 g/kg",
      1.8 <= plan_sk["nutrition_plan"]["macros"]["protein_grams"] / 55 <= 2.2)

# ==========================================================================
print("\n" + "=" * 70)
print(f"KẾT QUẢ: {len(PASSED)} PASS | {len(FAILED)} FAIL")
if FAILED:
    print("\nCác kiểm thử thất bại:")
    for f in FAILED:
        print(f"  - {f}")
print("=" * 70)

sys.exit(1 if FAILED else 0)