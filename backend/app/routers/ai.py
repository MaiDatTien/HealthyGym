"""Router AI Smart Fitness Coach — 4 bước nghiệp vụ.

Pipeline:
    POST /ai/diagnose        -> Bước 2 (khách vãng lai dùng thử, không cần đăng nhập)
    POST /ai/estimate-body-fat -> Nghiệp vụ phụ trợ US Navy Method
    POST /ai/plan            -> Bước 3 + 4 (xuất phác đồ đầy đủ, lưu vào hồ sơ)
    POST /ai/chat            -> Hội thoại tự nhiên theo Conversational Flow
    GET  /ai/onboarding      -> Chuỗi câu hỏi từng bước cho giao diện
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai import AIPlan, HealthMetric
from app.models.user import Member, User
from app.schemas.ai import (
    AIChatRequest,
    AIPlanRequest,
    BodyFatEstimateRequest,
    DiagnosisRequest,
)
from app.security import get_current_user, get_optional_user
from app.services import ai_coach, llm
from app.services.ai_diagnosis import (
    ACTIVITY_LABELS,
    BODY_FAT_LABELS_VI,
    GOAL_LABELS,
    bmi_category,
    calc_bmi,
    calc_bmr_katch_mcardle,
    calc_ffmi,
    calc_lean_body_mass,
    calc_tdee,
    classify_body_fat,
    classify_body_type,
    estimate_body_fat_us_navy,
    estimate_timeline,
    ffmi_interpretation,
    run_full_diagnosis,
)

router = APIRouter(prefix="/ai", tags=["AI Smart Fitness Coach"])


# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------
def _resolve_body_fat(req: DiagnosisRequest) -> tuple[float, Optional[str]]:
    """Xác định Body Fat %: dùng số nhập tay hoặc ước tính theo US Navy Method."""
    if req.body_fat_percentage is not None:
        return req.body_fat_percentage, None

    if req.neck_cm and req.waist_cm:
        bf = estimate_body_fat_us_navy(
            gender=req.gender,
            height_cm=req.height_cm,
            neck_cm=req.neck_cm,
            waist_cm=req.waist_cm,
            hip_cm=req.hip_cm,
        )
        return bf, "US Navy Method (ước tính từ số đo vòng cổ - eo - hông)"

    raise HTTPException(
        status_code=422,
        detail="Cần cung cấp 'body_fat_percentage', hoặc số đo 'neck_cm' + 'waist_cm' "
               "(và 'hip_cm' nếu là nữ) để hệ thống tự ước tính theo US Navy Method.",
    )


def _get_member_for_user(user: Optional[User], db: Session) -> Optional[Member]:
    if not user:
        return None
    return db.query(Member).filter(Member.user_id == user.id).first()


def _persist_metric_and_plan(
    member: Member, req: AIPlanRequest, plan: dict, db: Session
) -> tuple[HealthMetric, AIPlan]:
    """Lưu chỉ số sức khỏe + phác đồ AI vào hồ sơ hội viên."""
    d = plan["member_diagnosis"]

    # Vô hiệu hoá phác đồ cũ — chỉ giữ 1 phác đồ active
    db.query(AIPlan).filter(
        AIPlan.member_id == member.id, AIPlan.is_active == True
    ).update({"is_active": False}, synchronize_session=False)

    metric = HealthMetric(
        member_id=member.id,
        measured_at=date.today(),
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        body_fat_percentage=req.body_fat_percentage,
        age=req.age,
        gender=req.gender,
        waist_cm=getattr(req, "waist_cm", None),
        neck_cm=getattr(req, "neck_cm", None),
        hip_cm=getattr(req, "hip_cm", None),
        bmi=d["bmi"],
        lean_body_mass_kg=d["lean_body_mass_kg"],
        fat_mass_kg=d["fat_mass_kg"],
        bmr_kcal=d["bmr_kcal"],
        tdee_kcal=d["tdee_kcal"],
        body_type_classification=d["body_type_classification"],
        source="ai_coach",
        note="Sinh tự động bởi AI Smart Coach",
    )
    db.add(metric)
    db.flush()

    n = plan["nutrition_plan"]
    m = n["macros"]
    ai_plan = AIPlan(
        member_id=member.id,
        metric_id=metric.id,
        goal=req.goal,
        activity_level=req.activity_level,
        training_days_per_week=req.training_days_per_week,
        session_minutes=req.session_minutes,
        training_location=req.training_location,
        injuries=",".join(req.injuries or []),
        allergies=",".join(req.allergies or []),
        split_type=plan["workout_schedule"]["split_type"],
        target_daily_calories=n["target_daily_calories"],
        caloric_adjustment=n["caloric_adjustment"],
        protein_grams=m["protein_grams"],
        carbs_grams=m["carbs_grams"],
        fat_grams=m["fat_grams"],
        daily_water_liters=n["daily_water_liters"],
        estimated_weeks_to_goal=d["estimated_weeks_to_goal"],
        diagnosis_json=json.dumps(plan["member_diagnosis"], ensure_ascii=False),
        nutrition_json=json.dumps(plan["nutrition_plan"], ensure_ascii=False),
        workout_json=json.dumps(plan["workout_schedule"], ensure_ascii=False),
        recovery_json=json.dumps(plan["recovery_protocol"], ensure_ascii=False),
        summary_text=ai_coach.build_summary_text(plan),
        is_active=True,
    )
    db.add(ai_plan)
    db.commit()
    db.refresh(metric)
    db.refresh(ai_plan)
    return metric, ai_plan


def _plan_from_db(plan: AIPlan) -> dict:
    """Dựng lại JSON phác đồ từ các cột đã lưu."""
    return {
        "plan_id": plan.id,
        "goal": plan.goal,
        "goal_label": GOAL_LABELS.get(plan.goal, ""),
        "created_at": plan.created_at,
        "member_diagnosis": json.loads(plan.diagnosis_json) if plan.diagnosis_json else {},
        "nutrition_plan": json.loads(plan.nutrition_json) if plan.nutrition_json else {},
        "workout_schedule": json.loads(plan.workout_json) if plan.workout_json else {},
        "recovery_protocol": json.loads(plan.recovery_json) if plan.recovery_json else {},
        "summary_text": plan.summary_text,
        "is_active": plan.is_active,
    }


# --------------------------------------------------------------------------
# 1. METADATA
# --------------------------------------------------------------------------
@router.get("/onboarding")
def get_onboarding():
    """Chuỗi câu hỏi onboarding để giao diện render form từng bước."""
    return ai_coach.get_onboarding_flow()


@router.get("/options")
def get_options():
    """Toàn bộ danh mục lựa chọn (mục tiêu, mức vận động, chấn thương, dị ứng)."""
    return {
        "goals": [{"value": k, "label": v} for k, v in GOAL_LABELS.items()],
        "activity_levels": [
            {"value": k, "label": v} for k, v in ACTIVITY_LABELS.items()
        ],
        "body_fat_reference": {
            "male": [
                {"category": "Essential", "range": "2-5%", "note": "Mức tối thiểu sinh lý"},
                {"category": "Athletes", "range": "6-13%", "note": "Thể trạng thi đấu"},
                {"category": "Fitness", "range": "14-17%", "note": "Săn chắc, cơ nét"},
                {"category": "Average", "range": "18-24%", "note": "Còn mỡ thừa"},
                {"category": "Obese", "range": "≥25%", "note": "Cần giảm mỡ ưu tiên"},
            ],
            "female": [
                {"category": "Essential", "range": "10-13%", "note": "Mức tối thiểu sinh lý"},
                {"category": "Athletes", "range": "14-20%", "note": "Thể trạng thi đấu"},
                {"category": "Fitness", "range": "21-24%", "note": "Săn chắc, cơ nét"},
                {"category": "Average", "range": "25-31%", "note": "Còn mỡ thừa"},
                {"category": "Obese", "range": "≥32%", "note": "Cần giảm mỡ ưu tiên"},
            ],
        },
        "injuries": [
            {"value": "lower_back", "label": "Đau lưng dưới / Thoát vị đĩa đệm"},
            {"value": "knee", "label": "Đau khớp gối"},
            {"value": "shoulder", "label": "Đau khớp vai"},
            {"value": "wrist", "label": "Đau cổ tay"},
            {"value": "hip", "label": "Đau khớp hông"},
        ],
        "allergies": [
            {"value": "fish", "label": "Cá"},
            {"value": "seafood", "label": "Hải sản"},
            {"value": "egg", "label": "Trứng"},
            {"value": "dairy", "label": "Sữa & sản phẩm từ sữa"},
            {"value": "lactose", "label": "Không dung nạp lactose"},
            {"value": "peanut", "label": "Đậu phộng"},
            {"value": "nut", "label": "Các loại hạt"},
            {"value": "gluten", "label": "Gluten (lúa mì)"},
        ],
        "training_locations": [
            {"value": "gym", "label": "Tại phòng Gym (đầy đủ máy móc)"},
            {"value": "home_dumbbell", "label": "Tại nhà với tạ đơn"},
            {"value": "calisthenics", "label": "Calisthenics (trọng lượng cơ thể)"},
        ],
    }


@router.get("/system-instruction")
def get_system_instruction():
    """Trả về System Instruction và trạng thái cấu hình LLM.

    Dùng để nhúng vào LLM API (Gemini/OpenAI) hoặc kiểm tra xem chatbot đang
    chạy ở chế độ LLM hay engine rule-based nội bộ.
    """
    return {
        "system_instruction": ai_coach.SYSTEM_INSTRUCTION,
        "llm_enabled": llm.is_llm_enabled(),
        "llm_provider": llm.llm_config()["provider"] if llm.is_llm_enabled() else None,
        "llm_model": llm.llm_config()["model"] if llm.is_llm_enabled() else None,
        "json_schema_note": (
            "Gắn thêm quy định JSON Schema nghiệp vụ vào cuối API call để LLM trả về "
            "structured output. Endpoint /ai/plan sinh JSON này bằng engine nội bộ, "
            "không phụ thuộc LLM — nhờ đó các chỉ số luôn khớp tuyệt đối với phác đồ đã lưu "
            "và với biểu đồ tiến độ."
        ),
        "setup_hint": (
            "Để bật LLM, thêm vào backend/.env: LLM_PROVIDER=gemini, LLM_API_KEY=<key>, "
            "LLM_MODEL=gemini-2.0-flash (hoặc LLM_PROVIDER=openai với LLM_API_KEY=<key>). "
            "Khi chưa cấu hình, chatbot tự động dùng engine rule-based nội bộ."
        ),
    }


# --------------------------------------------------------------------------
# 2. ƯỚC TÍNH BODY FAT (US NAVY METHOD)
# --------------------------------------------------------------------------
@router.post("/estimate-body-fat")
def estimate_body_fat(req: BodyFatEstimateRequest):
    """Ước tính Body Fat % theo US Navy Method khi hội viên chưa đo InBody."""
    try:
        bf = estimate_body_fat_us_navy(
            gender=req.gender,
            height_cm=req.height_cm,
            neck_cm=req.neck_cm,
            waist_cm=req.waist_cm,
            hip_cm=req.hip_cm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    category = classify_body_fat(req.gender, bf)

    return {
        "body_fat_percentage": bf,
        "method": "US Navy Method",
        "category": category,
        "category_vi": BODY_FAT_LABELS_VI.get(category, ""),
        "inputs": {
            "gender": req.gender,
            "height_cm": req.height_cm,
            "neck_cm": req.neck_cm,
            "waist_cm": req.waist_cm,
            "hip_cm": req.hip_cm,
        },
        "accuracy_note": (
            "Phương pháp ước lượng từ số đo thước dây có sai số khoảng ±3-4% so với đo "
            "bằng máy InBody (DEXA có sai số ±1-2%). Nên đo vào buổi sáng, thước dây "
            "không siết chặt, đo tại vị trí rốn đối với nam và vị trí hẹp nhất đối với nữ."
        ),
    }


# --------------------------------------------------------------------------
# 3. BƯỚC 2: CHẨN ĐOÁN THỂ TRẠNG (Guest dùng thử miễn phí)
# --------------------------------------------------------------------------
@router.post("/diagnose")
def diagnose(req: DiagnosisRequest):
    """Bước 2 — Chẩn đoán thể trạng. Khách vãng lai dùng thử không cần đăng nhập."""
    body_fat, bf_source = _resolve_body_fat(req)

    result = run_full_diagnosis(
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        body_fat_percentage=body_fat,
        gender=req.gender,
        age=req.age,
        activity_level=req.activity_level,
        goal=req.goal,
    )

    return {
        "member_diagnosis": {
            "height_cm": req.height_cm,
            "weight_kg": req.weight_kg,
            "body_fat_percentage": body_fat,
            "body_fat_source": bf_source or "Hội viên cung cấp",
            "age": req.age,
            "gender": req.gender,
            "bmi": result.bmi,
            "bmi_category": result.bmi_category,
            "lean_body_mass_kg": result.lean_body_mass_kg,
            "fat_mass_kg": result.fat_mass_kg,
            "bmr_kcal": int(round(result.bmr_kcal)),
            "tdee_kcal": int(round(result.tdee_kcal)),
            "activity_multiplier": result.activity_multiplier,
            "activity_label": ACTIVITY_LABELS.get(req.activity_level, ""),
            "body_fat_category": result.body_fat_category,
            "body_fat_category_vi": result.body_fat_category_vi,
            "ffmi": result.ffmi,
            "ffmi_normalized": result.ffmi_normalized,
            "ffmi_interpretation": result.ffmi_interpretation,
            "muscle_quality": result.muscle_quality,
            "body_type": result.body_type,
            "body_type_classification": result.body_type_vi,
            "ai_assessment_summary": result.ai_assessment_summary,
            "estimated_weeks_to_goal": result.estimated_weeks_to_goal,
            "target_body_fat_percentage": result.target_body_fat_percentage,
            "fat_to_lose_kg": result.fat_to_lose_kg,
            "muscle_to_gain_kg": result.muscle_to_gain_kg,
            "weekly_fat_loss_target_kg": result.weekly_fat_loss_kg,
            "safety_warnings": result.warnings,
        },
        "goal": req.goal,
        "goal_label": GOAL_LABELS.get(req.goal, ""),
        "next_step": (
            "Cung cấp thêm số buổi tập/tuần, thời lượng mỗi buổi, nơi tập và tình trạng "
            "chấn thương tại POST /ai/plan để nhận phác đồ tập luyện + dinh dưỡng đầy đủ."
        ),
    }


# --------------------------------------------------------------------------
# 4. BƯỚC 3 + 4: XUẤT PHÁC ĐỒ ĐẦY ĐỦ
# --------------------------------------------------------------------------
@router.post("/plan")
def create_ai_plan(
    req: AIPlanRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Bước 3 + 4 — Lịch tập cá nhân hoá, dinh dưỡng & phục hồi.

    Khách vãng lai vẫn dùng được (không lưu hồ sơ). Hội viên đã đăng nhập sẽ được
    lưu vào HealthMetrics + AIPlans để theo dõi tiến độ.
    """
    plan = ai_coach.generate_full_plan(
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        body_fat_percentage=req.body_fat_percentage,
        gender=req.gender,
        age=req.age,
        activity_level=req.activity_level,
        goal=req.goal,
        training_days_per_week=req.training_days_per_week,
        session_minutes=req.session_minutes,
        training_location=req.training_location,
        injuries=req.injuries,
        allergies=req.allergies,
    )

    plan["summary_text"] = ai_coach.build_summary_text(plan)

    saved = False
    member = _get_member_for_user(current_user, db)
    if member and req.save_to_profile:
        metric, ai_plan = _persist_metric_and_plan(member, req, plan, db)
        plan["plan_id"] = ai_plan.id
        plan["metric_id"] = metric.id
        saved = True

    plan["saved_to_profile"] = saved
    return plan


@router.get("/plan/my")
def get_my_plan(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Phác đồ AI đang áp dụng của hội viên."""
    member = _get_member_for_user(current_user, db)
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hội viên")

    plan = (
        db.query(AIPlan)
        .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
        .order_by(AIPlan.created_at.desc())
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Bạn chưa có phác đồ AI nào. Hãy chạy chẩn đoán tại mục AI Smart Coach.",
        )
    return _plan_from_db(plan)


@router.get("/plan/history")
def get_plan_history(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Lịch sử các phác đồ AI đã sinh."""
    member = _get_member_for_user(current_user, db)
    if not member:
        return []
    plans = (
        db.query(AIPlan)
        .filter(AIPlan.member_id == member.id)
        .order_by(AIPlan.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "plan_id": p.id,
            "goal": p.goal,
            "goal_label": GOAL_LABELS.get(p.goal, ""),
            "split_type": p.split_type,
            "target_daily_calories": p.target_daily_calories,
            "estimated_weeks_to_goal": p.estimated_weeks_to_goal,
            "is_active": p.is_active,
            "created_at": p.created_at,
        }
        for p in plans
    ]


# --------------------------------------------------------------------------
# 5. HỘI THOẠI AI COACH
# --------------------------------------------------------------------------
@router.post("/chat")
def ai_chat(req: AIChatRequest, db: Session = Depends(get_db)):
    """Hội thoại với AI Smart Coach.

    Tuân thủ Conversational Flow: thu thập đủ chỉ số trước, rồi mới xuất phác đồ.

    Cách hoạt động:
      1. Nếu đã cấu hình LLM_API_KEY: gọi LLM với SYSTEM_INSTRUCTION chuẩn PT/Dinh dưỡng,
         kèm các chỉ số đã được engine nội bộ tính sẵn (LLM diễn giải, không tự tính).
      2. Nếu chưa cấu hình hoặc LLM lỗi: dùng engine rule-based nội bộ — website vẫn
         hoạt động đầy đủ, không phụ thuộc mạng.
    """
    context = {
        "estimate_body_fat": req.estimate_body_fat,
        "run_diagnosis": req.run_diagnosis,
    }
    if req.profile:
        context.update(req.profile)

    # Engine nội bộ luôn chạy trước: đảm bảo các hành động nghiệp vụ (ước tính Body Fat,
    # sinh phác đồ, tra cứu giá/lịch lớp) luôn chính xác và nhất quán.
    result = ai_coach.rule_based_reply(req.message, req.profile, context)

    # Bổ sung phần diễn giải tự nhiên từ LLM cho các câu hỏi tư vấn
    if result.get("action") not in ("plan_generated", "body_fat_estimated"):
        narrative = llm.ask_llm(
            ai_coach.SYSTEM_INSTRUCTION,
            req.message,
            profile=req.profile,
        )
        if narrative:
            result["reply"] = narrative
            result["llm_generated"] = True
    result.setdefault("llm_generated", False)

    # Lưu hội thoại để Admin xem lại chất lượng tư vấn
    try:
        from app.models.chat import ChatMessage

        db.add(
            ChatMessage(
                username=req.session_key or "guest",
                user_message=req.message,
                bot_response=result.get("reply", ""),
            )
        )
        db.commit()
    except Exception:
        db.rollback()

    return result


# --------------------------------------------------------------------------
# 6. CÔNG CỤ TÍNH NHANH TRÊN TRANG CHỦ
# --------------------------------------------------------------------------
@router.post("/quick-calc")
def quick_calc(req: DiagnosisRequest):
    """Công cụ tính nhanh TDEE & Body Fat cho trang chủ (không lưu dữ liệu)."""
    body_fat, bf_source = _resolve_body_fat(req)
    bmi = calc_bmi(req.weight_kg, req.height_cm)
    lbm = calc_lean_body_mass(req.weight_kg, body_fat)
    bmr = calc_bmr_katch_mcardle(lbm)
    tdee = calc_tdee(bmr, req.activity_level)
    ffmi, ffmi_norm = calc_ffmi(lbm, req.height_cm)
    bf_cat = classify_body_fat(req.gender, body_fat, req.age)

    timeline = estimate_timeline(
        req.goal, req.weight_kg, round(req.weight_kg - lbm, 2), lbm, req.gender
    )

    return {
        "bmi": bmi,
        "bmi_category": bmi_category(bmi),
        "body_fat_percentage": body_fat,
        "body_fat_source": bf_source or "Hội viên cung cấp",
        "body_fat_category": bf_cat,
        "body_fat_category_vi": BODY_FAT_LABELS_VI.get(bf_cat, ""),
        "lean_body_mass_kg": lbm,
        "fat_mass_kg": round(req.weight_kg - lbm, 2),
        "bmr_kcal": int(round(bmr)),
        "tdee_kcal": int(round(tdee)),
        "ffmi_normalized": ffmi_norm,
        "ffmi_interpretation": ffmi_interpretation(req.gender, ffmi_norm),
        "estimated_weeks_to_goal": timeline["estimated_weeks_to_goal"],
        "target_body_fat_percentage": timeline["target_body_fat_percentage"],
        "fat_to_lose_kg": timeline["fat_to_lose_kg"],
        "cta": "Đăng nhập và chạy chẩn đoán đầy đủ để nhận phác đồ tập luyện + "
               "thực đơn Việt Nam chi tiết theo gram.",
    }