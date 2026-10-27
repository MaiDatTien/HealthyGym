"""Router AI NÂNG CAO — Sàng lọc PAR-Q, InBody, đổi bài, đổi món,
chu kỳ hóa và đánh giá định kỳ.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai import (
    AIPlan, ChecklistItem, InBodyRecord, PARQScreening, WeeklyCheckin, WorkoutLog,
)
from app.models.interaction import now_local
from app.models.listing import Facility
from app.models.trainer_ops import PTPackagePurchase, PackageStatus
from app.models.user import Member, User
from app.schemas.erp import (
    CarbCyclingRequest, CheatMealRequest, DeloadRequest, ExerciseSwapRequest,
    FoodSwapRequest, InBodySubmit, OneRmRequest, PARQSubmit,
    ProgressiveOverloadRequest, WeeklyCheckinSubmit,
)
from app.security import get_current_user, get_optional_user, require_trainer_or_admin
from app.services import (
    ai_inbody, ai_nutrition_plus, ai_periodization, ai_screening, ai_coach,
)

router = APIRouter(prefix="/ai-plus", tags=["AI Advanced: PAR-Q, InBody, Periodization"])


def _member(user: User, db: Session) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hội viên")
    return member


def _resolve_member(
    user: Optional[User], member_id: Optional[int], db: Session
) -> Optional[Member]:
    """Xác định hội viên mục tiêu: ưu tiên member_id (cho HLV), nếu không lấy từ token."""
    if member_id:
        return db.query(Member).filter(Member.id == member_id).first()
    if user:
        return db.query(Member).filter(Member.user_id == user.id).first()
    return None


def _latest_parq(member_id: int, db: Session) -> Optional[PARQScreening]:
    return (
        db.query(PARQScreening)
        .filter(PARQScreening.member_id == member_id)
        .order_by(PARQScreening.screened_at.desc(), PARQScreening.id.desc())
        .first()
    )


def _contraindications_of(member_id: int, db: Session) -> list[str]:
    """Lấy danh sách mã cấm từ phiếu sàng lọc mới nhất."""
    screening = _latest_parq(member_id, db)
    if not screening or not screening.contraindications_json:
        return []
    try:
        return json.loads(screening.contraindications_json)
    except (json.JSONDecodeError, TypeError):
        return []


def _broken_exercise_names(branch_id: Optional[int], db: Session) -> list[str]:
    """Bài tập bị chặn do thiết bị đang bảo trì/ngưng dùng tại chi nhánh."""
    from app.models.engagement import MachineQR

    query = db.query(Facility).filter(
        Facility.lifecycle_status.in_(["maintenance", "out_of_order"])
    )
    if branch_id:
        query = query.filter(Facility.branch_id == branch_id)

    names: list[str] = []
    for f in query.all():
        for q in db.query(MachineQR).filter(
            MachineQR.facility_id == f.id, MachineQR.exercise_name != None
        ).all():
            if q.exercise_name:
                names.append(q.exercise_name)
    return names


# ==========================================================================
# BƯỚC 0: SÀNG LỌC AN TOÀN Y TẾ (PAR-Q+)
# ==========================================================================
@router.get("/parq/questions")
def parq_questions():
    """Bộ câu hỏi PAR-Q+ để giao diện render form sàng lọc."""
    return {
        "title": "Sàng lọc an toàn y tế (PAR-Q+)",
        "intro": (
            "Bảng câu hỏi này giúp AI Smart Coach thiết kế chương trình tập luyện AN TOÀN "
            "cho riêng bạn. Đây là bước BẮT BUỘC trước khi nhận lịch tập. "
            "Mọi thông tin sức khỏe của bạn được bảo mật."
        ),
        "parq_questions": [
            {"key": "q_heart_condition",
             "text": "Bác sĩ từng nói bạn có vấn đề về tim và chỉ nên tập luyện dưới sự giám sát y tế?"},
            {"key": "q_chest_pain",
             "text": "Bạn có bị đau ngực khi vận động thể lực không?"},
            {"key": "q_dizziness",
             "text": "Trong tháng qua, bạn có bị mất thăng bằng do chóng mặt hoặc từng bất tỉnh không?"},
            {"key": "q_chronic_disease",
             "text": "Bạn có đang được chẩn đoán bệnh tim, huyết áp cao, tiểu đường hoặc hen suyễn không?"},
            {"key": "q_bone_joint",
             "text": "Bạn có vấn đề về xương khớp (lưng, gối, vai) có thể nặng hơn khi vận động không?"},
            {"key": "q_medication",
             "text": "Bạn có đang dùng thuốc điều trị huyết áp hoặc tim mạch không?"},
            {"key": "q_other_reason",
             "text": "Có lý do sức khỏe nào khác khiến bạn không nên tập thể lực không?"},
        ],
        "detail_questions": [
            {"key": "has_herniated_disc",
             "text": "Bạn có bị thoát vị đĩa đệm hoặc đau lưng dưới không?",
             "follow_up": "disc_levels",
             "follow_up_hint": "VD: L4-L5, S1"},
            {"key": "has_cervical_degeneration",
             "text": "Bạn có bị thoái hóa đốt sống cổ không?"},
            {"key": "has_acl_tear",
             "text": "Bạn có bị đứt/rách dây chằng chéo (ACL) hoặc chấn thương khớp gối không?"},
            {"key": "has_rotator_cuff",
             "text": "Bạn có bị đau khớp vai hoặc chấn thương Rotator Cuff không?"},
            {"key": "has_heart_disease", "text": "Bạn có bệnh tim mạch không?"},
            {"key": "has_hypertension", "text": "Bạn có huyết áp cao không?"},
            {"key": "has_diabetes", "text": "Bạn có tiểu đường không?"},
            {"key": "has_asthma", "text": "Bạn có hen suyễn không?"},
            {"key": "is_pregnant", "text": "Bạn có đang mang thai không?"},
            {"key": "postpartum_months",
             "text": "Nếu bạn mới sinh, đã được bao nhiêu tháng?",
             "type": "number"},
        ],
        "hard_rules_note": (
            "Dựa trên câu trả lời, AI sẽ TỰ ĐỘNG loại bỏ các bài tập nguy hiểm. "
            "Ví dụ: thoát vị đĩa đệm → cấm Barbell Back Squat và Conventional Deadlift; "
            "béo phì độ II → cấm chạy tốc độ cao và nhảy dây; "
            "đau khớp vai → cấm đẩy tạ qua đầu."
        ),
    }


@router.post("/parq/submit")
def submit_parq(
    data: PARQSubmit,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Nộp bảng sàng lọc PAR-Q+ và nhận kết luận an toàn."""
    member = _resolve_member(current_user, data.member_id, db)

    # Lấy chỉ số cơ thể mới nhất để đánh giá béo phì
    bmi = None
    body_fat = None
    age = None
    gender = "male"
    if member:
        latest_metric = member.health_metrics[-1] if member.health_metrics else None
        if latest_metric:
            bmi = latest_metric.bmi
            body_fat = latest_metric.body_fat_percentage
            age = latest_metric.age
            gender = latest_metric.gender or "male"

    result = ai_screening.run_parq_screening(ai_screening.ScreeningInput(
        q_heart_condition=data.q_heart_condition,
        q_chest_pain=data.q_chest_pain,
        q_dizziness=data.q_dizziness,
        q_chronic_disease=data.q_chronic_disease,
        q_bone_joint=data.q_bone_joint,
        q_medication=data.q_medication,
        q_other_reason=data.q_other_reason,
        has_heart_disease=data.has_heart_disease,
        has_hypertension=data.has_hypertension,
        has_diabetes=data.has_diabetes,
        has_asthma=data.has_asthma,
        has_herniated_disc=data.has_herniated_disc,
        disc_levels=data.disc_levels,
        has_cervical_degeneration=data.has_cervical_degeneration,
        has_acl_tear=data.has_acl_tear,
        has_rotator_cuff=data.has_rotator_cuff,
        is_pregnant=data.is_pregnant,
        postpartum_months=data.postpartum_months,
        other_conditions=data.other_conditions,
        current_medications=data.current_medications,
        age=age,
        bmi=bmi,
        body_fat_percentage=body_fat,
        gender=gender,
    ))

    saved = False
    screening_id = None
    if member:
        screening = PARQScreening(
            member_id=member.id,
            screened_at=date.today(),
            q_heart_condition=data.q_heart_condition,
            q_chest_pain=data.q_chest_pain,
            q_dizziness=data.q_dizziness,
            q_chronic_disease=data.q_chronic_disease,
            q_bone_joint=data.q_bone_joint,
            q_medication=data.q_medication,
            q_other_reason=data.q_other_reason,
            has_heart_disease=data.has_heart_disease,
            has_hypertension=data.has_hypertension,
            has_diabetes=data.has_diabetes,
            has_asthma=data.has_asthma,
            has_herniated_disc=data.has_herniated_disc,
            disc_levels=data.disc_levels,
            has_cervical_degeneration=data.has_cervical_degeneration,
            has_acl_tear=data.has_acl_tear,
            has_rotator_cuff=data.has_rotator_cuff,
            is_pregnant=data.is_pregnant,
            postpartum_months=data.postpartum_months,
            other_conditions=data.other_conditions,
            current_medications=data.current_medications,
            needs_medical_clearance=result.needs_medical_clearance,
            risk_level=result.risk_level,
            clearance_required_note=result.clearance_note,
            contraindications_json=json.dumps(result.contraindications),
            safe_exercise_notes_json=json.dumps(
                result.safe_exercise_notes, ensure_ascii=False
            ),
            screened_by=current_user.full_name if current_user else "self",
        )
        db.add(screening)
        db.commit()
        db.refresh(screening)
        saved = True
        screening_id = screening.id

    return {
        "screening_id": screening_id,
        "saved": saved,
        "risk_level": result.risk_level,
        "parq_positive": result.parq_positive,
        "needs_medical_clearance": result.needs_medical_clearance,
        "clearance_note": result.clearance_note,
        "blocked_from_training": result.needs_medical_clearance,
        "contraindications": result.contraindications,
        "contraindication_labels": result.contraindication_labels,
        "safe_exercise_notes": result.safe_exercise_notes,
        "flags": result.flags,
        "next_step": (
            "⛔ Chưa thể lên lịch tập. Cần xác nhận y khoa trước."
            if result.needs_medical_clearance else
            "✅ Đủ điều kiện tập luyện. AI Workout Planner sẽ tự động áp dụng các "
            "ràng buộc an toàn khi sinh lịch tập."
        ),
        "applied_hard_rules": (
            [
                "AI sẽ TỰ ĐỘNG loại các bài tập nén trục cột sống nặng "
                "(Barbell Back Squat, Conventional Deadlift) và thay bằng bài an toàn "
                "(Belt Squat, Leg Press, Goblet Squat)."
            ]
            if ai_screening.Contraindication.NO_AXIAL_LOAD in result.contraindications
            else []
        ) + (
            [
                "AI sẽ TỰ ĐỘNG loại cardio chấn động (chạy tốc độ cao, nhảy dây, HIIT nhảy) "
                "và chuyển sang cardio không chấn động (đi bộ dốc, đạp xe tĩnh, bơi, elliptical)."
            ]
            if ai_screening.Contraindication.NO_HIGH_IMPACT in result.contraindications
            else []
        ) + (
            [
                "AI sẽ TỰ ĐỘNG loại các bài đẩy tạ qua đầu và thay bằng Landmine Press, "
                "đẩy tạ đơn tư thế trung lập."
            ]
            if ai_screening.Contraindication.NO_OVERHEAD_PRESS in result.contraindications
            else []
        ),
    }


@router.get("/parq/my")
def my_parq_screening(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Phiếu sàng lọc mới nhất của hội viên (AI Planner đọc để áp dụng ràng buộc)."""
    member = _member(current_user, db)
    screening = _latest_parq(member.id, db)
    if not screening:
        return {
            "has_screening": False,
            "message": (
                "Bạn chưa hoàn thành bảng sàng lọc an toàn y tế. "
                "Đây là bước bắt buộc trước khi nhận lịch tập."
            ),
            "action_required": "POST /ai-plus/parq/submit",
        }

    days_old = (date.today() - screening.screened_at).days
    return {
        "has_screening": True,
        "screening_id": screening.id,
        "screened_at": screening.screened_at,
        "days_since_screening": days_old,
        "is_expired": days_old > 365,
        "renewal_note": (
            "⚠️ Phiếu sàng lọc đã quá 12 tháng. Vui lòng cập nhật lại tình trạng sức khỏe."
            if days_old > 365 else None
        ),
        "risk_level": screening.risk_level,
        "needs_medical_clearance": screening.needs_medical_clearance,
        "clearance_note": screening.clearance_required_note,
        "contraindications": json.loads(screening.contraindications_json or "[]"),
        "safe_exercise_notes": json.loads(screening.safe_exercise_notes_json or "[]"),
        "conditions": {
            "heart_disease": screening.has_heart_disease,
            "hypertension": screening.has_hypertension,
            "diabetes": screening.has_diabetes,
            "asthma": screening.has_asthma,
            "herniated_disc": screening.has_herniated_disc,
            "disc_levels": screening.disc_levels,
            "cervical_degeneration": screening.has_cervical_degeneration,
            "acl_tear": screening.has_acl_tear,
            "rotator_cuff": screening.has_rotator_cuff,
            "pregnant": screening.is_pregnant,
            "postpartum_months": screening.postpartum_months,
        },
    }


# ==========================================================================
# PHÂN TÍCH INBODY CHUYÊN SÂU
# ==========================================================================
@router.post("/inbody/analyze")
def analyze_inbody(
    data: InBodySubmit,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Phân tích phiếu InBody chuyên sâu: SMM, mỡ nội tạng, C-I-D, mất cân bằng vùng."""
    member = _resolve_member(current_user, data.member_id, db)

    # Bổ sung dữ liệu còn thiếu từ hồ sơ
    height = data.height_cm
    weight = data.weight_kg
    body_fat = data.body_fat_percentage
    gender = data.gender
    age = data.age
    waist = data.waist_cm
    hip = data.hip_cm
    visceral = data.visceral_fat_level
    smm = data.skeletal_muscle_mass_kg

    if member:
        latest = member.health_metrics[-1] if member.health_metrics else None
        if latest:
            height = height or latest.height_cm
            weight = weight or latest.weight_kg
            body_fat = body_fat if body_fat is not None else latest.body_fat_percentage
            gender = latest.gender or gender
            age = age or latest.age
            waist = waist or latest.waist_cm
            visceral = visceral if visceral is not None else latest.visceral_fat_level
            smm = smm or latest.muscle_mass_kg

    result = ai_inbody.analyze_inbody(
        height_cm=height,
        weight_kg=weight,
        body_fat_percentage=body_fat,
        skeletal_muscle_mass_kg=smm,
        body_fat_mass_kg=data.body_fat_mass_kg,
        visceral_fat_level=visceral,
        waist_cm=waist,
        hip_cm=hip,
        gender=gender,
        age=age,
        lean_left_arm=data.lean_left_arm,
        lean_right_arm=data.lean_right_arm,
        lean_trunk=data.lean_trunk,
        lean_left_leg=data.lean_left_leg,
        lean_right_leg=data.lean_right_leg,
        fat_left_arm=data.fat_left_arm,
        fat_right_arm=data.fat_right_arm,
        fat_trunk=data.fat_trunk,
        fat_left_leg=data.fat_left_leg,
        fat_right_leg=data.fat_right_leg,
    )

    saved = False
    record_id = None
    deltas = {}
    if member and data.save_to_profile:
        previous = (
            db.query(InBodyRecord)
            .filter(InBodyRecord.member_id == member.id)
            .order_by(InBodyRecord.measured_at.desc(), InBodyRecord.id.desc())
            .first()
        )

        delta_muscle = None
        delta_fat = None
        if previous:
            if previous.skeletal_muscle_mass_kg and smm:
                delta_muscle = round(smm - previous.skeletal_muscle_mass_kg, 2)
            if previous.body_fat_mass_kg and data.body_fat_mass_kg:
                delta_fat = round(data.body_fat_mass_kg - previous.body_fat_mass_kg, 2)
            deltas = {
                "previous_measured_at": previous.measured_at,
                "delta_muscle_kg": delta_muscle,
                "delta_fat_kg": delta_fat,
                "interpretation": (
                    "🎉 Tăng cơ và giảm mỡ đồng thời — Body Recomposition đang hoạt động tốt!"
                    if delta_muscle and delta_muscle > 0 and delta_fat and delta_fat < 0
                    else (
                        "Cơ tăng nhưng mỡ cũng tăng — bình thường trong giai đoạn Lean Bulk. "
                        "Nếu muốn siết nét, giảm nhẹ 200 kcal/ngày."
                        if delta_muscle and delta_muscle > 0 and delta_fat and delta_fat > 0
                        else (
                            "⚠️ Cơ giảm — cần kiểm tra lại lượng đạm và khối lượng tập."
                            if delta_muscle and delta_muscle < -0.3
                            else "Chỉ số ổn định, tiếp tục duy trì."
                        )
                    )
                ),
            }

        record = InBodyRecord(
            member_id=member.id,
            measured_at=data.measured_at or date.today(),
            skeletal_muscle_mass_kg=smm,
            body_fat_mass_kg=data.body_fat_mass_kg,
            body_fat_percentage=body_fat,
            visceral_fat_level=visceral,
            body_water_kg=data.body_water_kg,
            protein_kg=data.protein_kg,
            mineral_kg=data.mineral_kg,
            bmi=round(weight / ((height / 100) ** 2), 2) if weight and height else None,
            basal_metabolic_rate=data.basal_metabolic_rate,
            waist_hip_ratio=result.whr,
            lean_left_arm=data.lean_left_arm,
            lean_right_arm=data.lean_right_arm,
            lean_trunk=data.lean_trunk,
            lean_left_leg=data.lean_left_leg,
            lean_right_leg=data.lean_right_leg,
            fat_left_arm=data.fat_left_arm,
            fat_right_arm=data.fat_right_arm,
            fat_trunk=data.fat_trunk,
            fat_left_leg=data.fat_left_leg,
            fat_right_leg=data.fat_right_leg,
            shape_type=result.shape_type,
            shape_description=result.shape_description,
            balance_score=result.segmental.balance_score,
            imbalances_json=json.dumps(
                result.segmental.imbalances, ensure_ascii=False
            ),
            recommendations_json=json.dumps(
                result.segmental.recommendations + result.priority_actions,
                ensure_ascii=False,
            ),
            delta_muscle_kg=delta_muscle,
            delta_fat_kg=delta_fat,
            device_model=data.device_model,
            note=data.note,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        saved = True
        record_id = record.id

    return {
        "record_id": record_id,
        "saved": saved,
        "shape": {
            "type": result.shape_type,
            "description": result.shape_description,
            "rationale": result.shape_rationale,
        },
        "visceral_fat": {
            "level": result.visceral_fat_level,
            "status": result.visceral_fat_status,
            "is_warning": (
                result.visceral_fat_level is not None
                and result.visceral_fat_level >= ai_inbody.VISCERAL_FAT_NORMAL_MAX
            ),
        },
        "whr": {"value": result.whr, "status": result.whr_status},
        "smm_ratio": {"value": result.smm_ratio, "status": result.smm_ratio_status},
        "segmental_analysis": {
            "has_data": result.segmental.has_data,
            "arm_difference_kg": result.segmental.arm_difference_kg,
            "arm_difference_percent": result.segmental.arm_difference_percent,
            "leg_difference_kg": result.segmental.leg_difference_kg,
            "leg_difference_percent": result.segmental.leg_difference_percent,
            "balance_score": result.segmental.balance_score,
            "imbalances": result.segmental.imbalances,
            "recommendations": result.segmental.recommendations,
        },
        "priority_actions": result.priority_actions,
        "training_adjustments": result.training_adjustments,
        "goal_recommendation": result.goal_recommendation,
        "warnings": result.warnings,
        "comparison": deltas or None,
        "summary": result.summary,
    }


@router.get("/inbody/history")
def inbody_history(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Lịch sử đo InBody và xu hướng thay đổi."""
    member = _member(current_user, db)
    records = (
        db.query(InBodyRecord)
        .filter(InBodyRecord.member_id == member.id)
        .order_by(InBodyRecord.measured_at.asc())
        .all()
    )

    return {
        "total_records": len(records),
        "records": [
            {
                "id": r.id,
                "measured_at": r.measured_at,
                "smm_kg": r.skeletal_muscle_mass_kg,
                "body_fat_kg": r.body_fat_mass_kg,
                "body_fat_percentage": r.body_fat_percentage,
                "visceral_fat_level": r.visceral_fat_level,
                "shape_type": r.shape_type,
                "balance_score": r.balance_score,
                "delta_muscle_kg": r.delta_muscle_kg,
                "delta_fat_kg": r.delta_fat_kg,
                "device_model": r.device_model,
            }
            for r in records
        ],
        "trend": {
            "labels": [str(r.measured_at) for r in records],
            "smm": [r.skeletal_muscle_mass_kg for r in records],
            "body_fat_kg": [r.body_fat_mass_kg for r in records],
            "visceral_fat": [r.visceral_fat_level for r in records],
            "balance_score": [r.balance_score for r in records],
        } if records else None,
    }


# ==========================================================================
# ĐỔI BÀI TẬP TỨC THÌ & CHU KỲ HÓA
# ==========================================================================
@router.post("/swap-exercise")
def swap_exercise(
    data: ExerciseSwapRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Đổi bài tập tức thì khi máy hỏng / có người dùng / đau khớp.

    Tự động tôn trọng chấn thương (từ phiếu PAR-Q) và thiết bị đang hỏng.
    """
    member = _resolve_member(current_user, None, db)

    injuries: list[str] = []
    contraindications: list[str] = []
    if member:
        injuries = _contraindications_of(member.id, db)
        contraindications = injuries

    broken = _broken_exercise_names(data.branch_id, db)

    # Nếu hội viên chọn lý do 'máy hỏng' mà chưa truyền branch, vẫn lọc theo toàn hệ thống
    result = ai_periodization.find_substitutes(
        exercise_name=data.exercise_name,
        reason=data.reason,
        injuries=injuries,
        broken_equipment_names=broken,
        max_results=data.max_results,
    )

    # Bổ sung cảnh báo nếu hội viên đang đau khớp
    if data.reason == "joint_pain":
        result["safety_note"] = (
            "⚠️ Bạn đang đau khớp khi tập bài này. Hãy giảm mức tạ 20-30% ở bài thay thế "
            "và tập thử 1 hiệp nhẹ trước. Nếu vẫn đau, DỪNG LẠI và báo cho HLV — "
            "đau khớp không phải là điều nên 'tập cho quen'."
        )
        result["when_to_stop"] = [
            "Đau nhói hoặc đau chói tại một điểm cụ thể trên khớp.",
            "Khớp phát ra tiếng lục cục kèm đau.",
            "Sưng hoặc nóng đỏ vùng khớp sau khi tập.",
            "Đau kéo dài hơn 48 giờ sau buổi tập.",
        ]

    if contraindications:
        result["injury_context"] = {
            "active_contraindications": contraindications,
            "note": (
                "Các gợi ý trên đã được lọc để KHÔNG xung đột với chấn thương/bệnh lý "
                "trong phiếu sàng lọc PAR-Q của bạn."
            ),
        }

    if broken:
        result["equipment_context"] = {
            "unavailable_equipment_exercises": broken,
            "note": "Các bài tập dùng thiết bị đang bảo trì đã bị loại khỏi gợi ý.",
        }

    return result


@router.post("/one-rm")
def calculate_one_rm(data: OneRmRequest):
    """Ước tính 1RM theo công thức Epley và Brzycki."""
    epley = ai_periodization.estimate_1rm(data.weight_kg, data.reps)
    brzycki = ai_periodization.estimate_1rm_brzycki(data.weight_kg, data.reps)
    best = ai_periodization.average_1rm(data.weight_kg, data.reps)

    accuracy_note = (
        "Độ chính xác cao (sai số ~2-3%)."
        if 1 <= data.reps <= 6 else
        (
            "Độ chính xác khá tốt (sai số ~3-5%)."
            if data.reps <= 10 else
            "⚠️ Trên 10 reps, sai số ước tính tăng đáng kể (>8%). "
            "Nên test với mức tạ nặng hơn ở 3-6 reps để có con số chính xác."
        )
    )

    zones = {
        goal: ai_periodization.training_load_for_goal(best, goal)
        for goal in ("strength", "hypertrophy", "endurance")
    }

    return {
        "weight_kg": data.weight_kg,
        "reps": data.reps,
        "estimated_1rm": {
            "epley": epley,
            "brzycki": brzycki,
            "recommended": best,
        },
        "accuracy_note": accuracy_note,
        "training_zones": zones,
        "usage_note": (
            "Dùng các vùng tải trọng bên dưới để chọn mức tạ cho từng mục tiêu. "
            "Ví dụ: để tập phì đại cơ, dùng 67-80% của 1RM với 6-12 reps."
        ),
        "safety_warning": (
            "Không nên test 1RM thật (đẩy 1 lần tối đa) nếu bạn tập dưới 6 tháng "
            "hoặc có chấn thương. Ước tính từ 3-6 reps an toàn hơn nhiều."
        ),
    }


@router.post("/deload/check")
def check_deload(
    data: DeloadRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Kiểm tra có cần tuần giảm tải (Deload) hay không, và sinh kế hoạch."""
    needed = ai_periodization.should_deload(data.weeks_training, data.deload_count)

    member = _resolve_member(current_user, None, db)
    plan = None
    if member:
        active_plan = (
            db.query(AIPlan)
            .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
            .order_by(AIPlan.created_at.desc())
            .first()
        )
        if active_plan and active_plan.workout_json and needed:
            workout = json.loads(active_plan.workout_json)
            plan = ai_periodization.build_deload_plan(
                workout.get("sessions", []), data.weeks_training
            )

    weeks_until = max(
        0,
        ai_periodization.DELOAD_AFTER_WEEKS
        - (data.weeks_training - data.deload_count * ai_periodization.DELOAD_AFTER_WEEKS),
    )

    return {
        "should_deload": needed,
        "weeks_training": data.weeks_training,
        "deloads_taken": data.deload_count,
        "weeks_until_next_deload": weeks_until,
        "recommendation": (
            "✅ ĐÃ ĐẾN LÚC DELOAD. Bạn đã tập nặng liên tục "
            f"{ai_periodization.DELOAD_AFTER_WEEKS} tuần. Hãy dành 1 tuần giảm tải."
            if needed else
            f"Chưa cần Deload. Còn {weeks_until} tuần nữa mới đến mốc giảm tải."
        ),
        "deload_plan": plan,
        "reasons_to_deload": [
            "Hệ thần kinh trung ương (CNS) cần thời gian hồi phục — đây thường là "
            "yếu tố giới hạn sức mạnh, không phải cơ bắp.",
            "Gân và dây chằng phục hồi chậm hơn cơ — Deload giúp phòng chấn thương.",
            "Giúp phá vỡ trạng thái chững sức mạnh (plateau).",
            "Cải thiện chất lượng giấc ngủ và tâm lý tập luyện.",
        ],
        "signs_you_need_deload_now": [
            "Nhịp tim nghỉ tăng trên 5 bpm so với bình thường.",
            "Sức mạnh giảm 2 buổi liên tiếp dù ăn ngủ đủ.",
            "Đau khớp hoặc gân kéo dài, không phải đau cơ.",
            "Mất ngủ, cáu gắt, mất động lực tập.",
        ],
    }


@router.post("/progressive-overload")
def progressive_overload(
    data: ProgressiveOverloadRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Đánh giá tăng tiến mức tạ cho buổi kế tiếp."""
    decision = ai_periodization.evaluate_progressive_overload(
        exercise_name=data.exercise_name,
        last_sets=data.sets,
        target_reps_upper=data.target_reps_upper,
    )

    member = _resolve_member(current_user, None, db)
    history = None
    if member:
        logs = (
            db.query(WorkoutLog)
            .filter(
                WorkoutLog.member_id == member.id,
                WorkoutLog.exercise_name == data.exercise_name,
                WorkoutLog.weight_kg != None,
            )
            .order_by(WorkoutLog.log_date.desc())
            .limit(8)
            .all()
        )
        if logs:
            history = {
                "sessions": [
                    {
                        "date": w.log_date,
                        "sets": w.sets,
                        "reps": w.reps,
                        "weight_kg": w.weight_kg,
                        "rpe": w.rpe,
                        "volume": round((w.sets or 0) * (w.reps or 0) * (w.weight_kg or 0)),
                    }
                    for w in reversed(logs)
                ],
                "trend": (
                    "increasing"
                    if len(logs) >= 2 and (logs[0].weight_kg or 0) > (logs[-1].weight_kg or 0)
                    else ("decreasing" if len(logs) >= 2
                          and (logs[0].weight_kg or 0) < (logs[-1].weight_kg or 0)
                          else "stable")
                ),
            }

    return {
        "exercise_name": decision.exercise_name,
        "action": decision.action,
        "action_label": {
            "increase": "TĂNG TẠ",
            "maintain": "GIỮ NGUYÊN",
            "decrease": "GIẢM TẠ",
            "deload": "GIẢM TẢI",
        }.get(decision.action, decision.action),
        "current_weight_kg": decision.current_weight_kg,
        "suggested_weight_kg": decision.suggested_weight_kg,
        "increment_kg": decision.increment_kg,
        "reason": decision.reason,
        "confidence": decision.confidence,
        "notes": decision.notes,
        "history": history,
        "progression_principle": (
            "Nguyên tắc Progressive Overload: tăng dần kích thích để cơ thể tiếp tục "
            "thích nghi. Có thể tăng qua: mức tạ, số reps, số hiệp, hoặc giảm thời gian nghỉ — "
            "nhưng chỉ nên tăng MỘT biến số mỗi lần."
        ),
    }


# ==========================================================================
# ĐỔI MÓN, CARB CYCLING & BÙ TRỪ CHEAT MEAL
# ==========================================================================
@router.get("/foods/list")
def list_foods():
    """Danh sách thực phẩm trong cơ sở dữ liệu dinh dưỡng (kèm nhóm vai trò)."""
    from app.services.ai_nutrition import FOOD_DB

    items = []
    for key, food in FOOD_DB.items():
        role = ai_nutrition_plus.find_food_role(key)
        items.append({
            "key": key,
            "name": food["name"],
            "kcal_per_100g": food["kcal"],
            "protein_per_100g": food["p"],
            "carbs_per_100g": food["c"],
            "fat_per_100g": food["f"],
            "role": role,
            "role_label": ai_nutrition_plus.ROLE_LABELS.get(role or "", ""),
            "allergen_tags": food.get("tags", []),
        })

    return {
        "total": len(items),
        "roles": [
            {"key": k, "label": v}
            for k, v in ai_nutrition_plus.ROLE_LABELS.items()
        ],
        "foods": sorted(items, key=lambda x: (x["role"] or "zz", x["name"])),
    }


@router.post("/swap-food")
def swap_food(
    data: FoodSwapRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Đổi thực phẩm tương đương — tự quy đổi gram để giữ nguyên protein và calo."""
    member = _resolve_member(current_user, None, db)

    allergies: list[str] = []
    if member:
        active_plan = (
            db.query(AIPlan)
            .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
            .order_by(AIPlan.created_at.desc())
            .first()
        )
        if active_plan and active_plan.allergies:
            allergies = [
                a.strip() for a in active_plan.allergies.split(",") if a.strip()
            ]

    result = ai_nutrition_plus.suggest_food_swaps(
        food_key=data.food_key,
        current_grams=data.grams,
        allergies=allergies,
        max_results=data.max_results,
        prioritize=data.prioritize,
    )

    if allergies:
        result["allergy_context"] = {
            "allergies_applied": allergies,
            "note": "Các thực phẩm gây dị ứng của bạn đã được loại khỏi danh sách gợi ý.",
        }

    return result


@router.post("/carb-cycling")
def carb_cycling(data: CarbCyclingRequest):
    """Thiết kế chu kỳ Carb Cycling trong tuần."""
    macros = {
        "protein_grams": data.protein_g,
        "carbs_grams": data.carbs_g,
        "fat_grams": data.fat_g,
    }
    return ai_nutrition_plus.build_carb_cycling(
        base_calories=data.target_calories,
        protein_g=data.protein_g,
        carbs_g=data.carbs_g,
        fat_g=data.fat_g,
        training_days_per_week=data.training_days_per_week,
        goal=data.goal,
    )


@router.post("/cheat-meal-recovery")
def cheat_meal_recovery(
    data: CheatMealRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Tính phương án bù trừ khi ăn lố — KHÔNG bắt nhịn đói."""
    member = _resolve_member(current_user, None, db)

    # Lấy calo mục tiêu và cân nặng
    target_calories = 2000.0
    weight_kg = 70.0

    if member:
        active_plan = (
            db.query(AIPlan)
            .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
            .order_by(AIPlan.created_at.desc())
            .first()
        )
        if active_plan and active_plan.target_daily_calories:
            target_calories = active_plan.target_daily_calories
        latest_metric = member.health_metrics[-1] if member.health_metrics else None
        if latest_metric and latest_metric.weight_kg:
            weight_kg = latest_metric.weight_kg

    return ai_nutrition_plus.calculate_cheat_meal_compensation(
        excess_calories=data.excess_calories,
        target_calories=target_calories,
        weight_kg=weight_kg,
        days_available=data.days_available,
        meal_description=data.meal_description or "",
    )


# ==========================================================================
# ĐÁNH GIÁ ĐỊNH KỲ HÀNG TUẦN & HIỆU CHỈNH ĐỘNG
# ==========================================================================
@router.get("/weekly-checkin/form")
def weekly_checkin_form(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Form đánh giá định kỳ Chủ Nhật kèm dữ liệu tuần trước để so sánh."""
    member = _member(current_user, db)

    active_plan = (
        db.query(AIPlan)
        .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
        .order_by(AIPlan.created_at.desc())
        .first()
    )

    last_checkin = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.member_id == member.id)
        .order_by(WeeklyCheckin.week_start.desc())
        .first()
    )

    # Dữ liệu tuần vừa qua
    week_ago = date.today() - timedelta(days=7)
    recent_metric = (
        member.health_metrics[-1] if member.health_metrics else None
    )

    from app.models.operations import GateCheckin, GateResult
    visits = (
        db.query(func.count(GateCheckin.id))
        .filter(
            GateCheckin.member_id == member.id,
            GateCheckin.result == GateResult.GRANTED,
            GateCheckin.checkin_time >= datetime.combine(week_ago, datetime.min.time()),
        )
        .scalar()
        or 0
    )
    logged_workouts = (
        db.query(func.count(func.distinct(WorkoutLog.log_date)))
        .filter(
            WorkoutLog.member_id == member.id,
            WorkoutLog.log_date >= week_ago,
        )
        .scalar()
        or 0
    )

    return {
        "week_start": str(date.today() - timedelta(days=date.today().weekday())),
        "planned_sessions": active_plan.training_days_per_week if active_plan else 4,
        "actual_visits": visits,
        "logged_workout_days": logged_workouts,
        "latest_weight_kg": recent_metric.weight_kg if recent_metric else None,
        "latest_waist_cm": recent_metric.waist_cm if recent_metric else None,
        "previous_checkin": {
            "week_start": last_checkin.week_start,
            "avg_weight_kg": last_checkin.avg_weight_kg,
            "detected_issue": last_checkin.detected_issue,
            "ai_feedback": last_checkin.ai_feedback,
        } if last_checkin else None,
        "questions": [
            {"key": "avg_weight_kg", "text": "Cân nặng trung bình tuần này (kg)",
             "hint": "Cân 3-4 lần vào buổi sáng lúc bụng đói rồi lấy trung bình"},
            {"key": "waist_cm", "text": "Số đo vòng eo (cm)",
             "hint": "Đo tại vị trí rốn, thước không siết chặt"},
            {"key": "sessions_completed", "text": "Số buổi tập thực tế đã hoàn thành"},
            {"key": "hunger_level", "text": "Mức độ đói (1-5)",
             "hint": "1 = rất thoải mái, 5 = đói cồn cào"},
            {"key": "sleep_quality", "text": "Chất lượng giấc ngủ (1-5)",
             "hint": "1 = rất kém, 5 = ngủ sâu ngon"},
            {"key": "energy_level", "text": "Mức năng lượng (1-5)"},
            {"key": "stress_level", "text": "Mức căng thẳng (1-5)"},
            {"key": "adherence_percent", "text": "Mức tuân thủ dinh dưỡng (%)",
             "hint": "Ước lượng % số bữa ăn đúng kế hoạch"},
        ],
        "why_this_matters": (
            "Đánh giá định kỳ giúp AI phát hiện sớm chững cân (plateau) và mất cơ — "
            "từ đó điều chỉnh calo chính xác. Không có dữ liệu này, AI chỉ có thể "
            "đoán và kế hoạch sẽ kém hiệu quả."
        ),
    }


@router.post("/weekly-checkin")
def submit_weekly_checkin(
    data: WeeklyCheckinSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nộp đánh giá định kỳ — AI phân tích và tự động hiệu chỉnh kế hoạch."""
    member = _member(current_user, db)

    week_start = date.today() - timedelta(days=date.today().weekday())

    existing = (
        db.query(WeeklyCheckin)
        .filter(
            WeeklyCheckin.member_id == member.id,
            WeeklyCheckin.week_start == week_start,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Bạn đã nộp đánh giá cho tuần bắt đầu {week_start} rồi.",
        )

    active_plan = (
        db.query(AIPlan)
        .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
        .order_by(AIPlan.created_at.desc())
        .first()
    )

    # --- Tính thay đổi cân nặng ---
    previous_checkin = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.member_id == member.id)
        .order_by(WeeklyCheckin.week_start.desc())
        .first()
    )

    weight_change = None
    weight_change_percent = 0.0
    baseline_weight = None

    if data.avg_weight_kg:
        if previous_checkin and previous_checkin.avg_weight_kg:
            baseline_weight = previous_checkin.avg_weight_kg
        else:
            latest_metric = member.health_metrics[-1] if member.health_metrics else None
            baseline_weight = latest_metric.weight_kg if latest_metric else None

        if baseline_weight:
            weight_change = round(data.avg_weight_kg - baseline_weight, 2)
            weight_change_percent = round(weight_change / baseline_weight * 100, 2)

    # --- Phát hiện chững cân ---
    weeks_stalled = 0
    if abs(weight_change_percent) < 0.3:
        weeks_stalled = 1
        # Đếm ngược các tuần trước cũng chững
        prior = (
            db.query(WeeklyCheckin)
            .filter(WeeklyCheckin.member_id == member.id)
            .order_by(WeeklyCheckin.week_start.desc())
            .limit(4)
            .all()
        )
        for p in prior:
            if p.weight_change_percent is not None and abs(p.weight_change_percent) < 0.3:
                weeks_stalled += 1
            else:
                break

    # --- Phát hiện mất cơ (sụt quá nhanh hoặc tụt tạ) ---
    strength_dropped = False
    recent_logs = (
        db.query(WorkoutLog)
        .filter(
            WorkoutLog.member_id == member.id,
            WorkoutLog.weight_kg != None,
            WorkoutLog.log_date >= date.today() - timedelta(days=14),
        )
        .order_by(WorkoutLog.log_date.desc())
        .limit(20)
        .all()
    )
    older_logs = (
        db.query(WorkoutLog)
        .filter(
            WorkoutLog.member_id == member.id,
            WorkoutLog.weight_kg != None,
            WorkoutLog.log_date < date.today() - timedelta(days=14),
            WorkoutLog.log_date >= date.today() - timedelta(days=42),
        )
        .limit(20)
        .all()
    )
    if recent_logs and older_logs:
        recent_avg = sum(w.weight_kg for w in recent_logs) / len(recent_logs)
        older_avg = sum(w.weight_kg for w in older_logs) / len(older_logs)
        if recent_avg < older_avg * 0.95:
            strength_dropped = True

    # --- Hiệu chỉnh động ---
    target_calories = active_plan.target_daily_calories if active_plan else 2000
    base_tdee = (
        json.loads(active_plan.diagnosis_json).get("tdee_kcal", 2400)
        if active_plan and active_plan.diagnosis_json else 2400
    )

    adjustment = ai_nutrition_plus.build_weekly_recalibration(
        current_target_calories=target_calories or 2000,
        base_tdee=base_tdee,
        weekly_weight_change_percent=weight_change_percent,
        weeks_stalled=weeks_stalled,
        adherence_percent=data.adherence_percent or 100,
        strength_dropped=strength_dropped,
        weeks_in_deficit=max(0, (date.today() - active_plan.created_at.date()).days // 7)
        if active_plan and active_plan.created_at else 0,
        hunger_level=data.hunger_level,
        sleep_quality=data.sleep_quality,
    )

    # --- Ghi nhận ---
    checkin = WeeklyCheckin(
        member_id=member.id,
        ai_plan_id=active_plan.id if active_plan else None,
        week_start=week_start,
        avg_weight_kg=data.avg_weight_kg,
        waist_cm=data.waist_cm,
        sessions_completed=data.sessions_completed,
        sessions_planned=data.sessions_planned or (
            active_plan.training_days_per_week if active_plan else 4
        ),
        hunger_level=data.hunger_level,
        sleep_quality=data.sleep_quality,
        energy_level=data.energy_level,
        stress_level=data.stress_level,
        adherence_percent=data.adherence_percent,
        note=data.note,
        weight_change_kg=weight_change,
        weight_change_percent=weight_change_percent,
        detected_issue=adjustment["issue_detected"],
        adjustment_type=adjustment["adjustment"]["action"],
        adjustment_detail=adjustment["adjustment"]["reason"],
        calorie_delta=adjustment["adjustment"]["calorie_delta"],
        ai_feedback=adjustment["ai_feedback"],
    )
    db.add(checkin)

    # --- Tự động tạo checklist nếu có điều chỉnh ---
    if adjustment["adjustment"]["action"] != "maintain":
        db.add(ChecklistItem(
            member_id=member.id,
            title=(
                f"Điều chỉnh dinh dưỡng: "
                f"{adjustment['adjustment']['calorie_delta']:+.0f} kcal/ngày"
            ),
            detail=adjustment["adjustment"]["reason"],
            source="ai",
            due_date=date.today() + timedelta(days=7),
        ))

    for note in adjustment["extra_notes"]:
        db.add(ChecklistItem(
            member_id=member.id,
            title="Lưu ý từ AI Coach",
            detail=note,
            source="ai",
            due_date=date.today() + timedelta(days=7),
        ))

    db.commit()
    db.refresh(checkin)

    return {
        "checkin_id": checkin.id,
        "week_start": week_start,
        "weight_change_kg": weight_change,
        "weight_change_percent": weight_change_percent,
        "detected_issue": adjustment["issue_detected"],
        "issue_label": {
            "on_track": "Đúng tiến độ",
            "plateau": "Chững cân",
            "muscle_loss": "Có dấu hiệu mất cơ",
        }.get(adjustment["issue_detected"], adjustment["issue_detected"]),
        "adjustment": adjustment["adjustment"],
        "extra_notes": adjustment["extra_notes"],
        "monitoring": adjustment["monitoring"],
        "ai_feedback": adjustment["ai_feedback"],
        "next_checkin_note": adjustment["next_checkin_note"],
        "safety_note": (
            "⚠️ AI không bao giờ khuyến nghị nhịn đói hay cắt calo cực đoan. "
            "Mọi điều chỉnh đều nằm trong ngưỡng an toàn 150-300 kcal và không "
            "xuống dưới 1.200 kcal/ngày."
        ),
    }


@router.get("/weekly-checkin/history")
def weekly_checkin_history(
    limit: int = Query(12, ge=1, le=52),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lịch sử đánh giá định kỳ và xu hướng."""
    member = _member(current_user, db)
    checkins = (
        db.query(WeeklyCheckin)
        .filter(WeeklyCheckin.member_id == member.id)
        .order_by(WeeklyCheckin.week_start.desc())
        .limit(limit)
        .all()
    )

    issues = {}
    for c in checkins:
        if c.detected_issue:
            issues[c.detected_issue] = issues.get(c.detected_issue, 0) + 1

    return {
        "total_checkins": len(checkins),
        "issue_summary": issues,
        "checkins": [
            {
                "week_start": c.week_start,
                "avg_weight_kg": c.avg_weight_kg,
                "weight_change_kg": c.weight_change_kg,
                "weight_change_percent": c.weight_change_percent,
                "sessions_completed": c.sessions_completed,
                "sessions_planned": c.sessions_planned,
                "adherence_percent": c.adherence_percent,
                "hunger_level": c.hunger_level,
                "sleep_quality": c.sleep_quality,
                "detected_issue": c.detected_issue,
                "adjustment_type": c.adjustment_type,
                "calorie_delta": c.calorie_delta,
                "ai_feedback": c.ai_feedback,
            }
            for c in checkins
        ],
        "trend": {
            "labels": [str(c.week_start) for c in reversed(checkins)],
            "weight": [c.avg_weight_kg for c in reversed(checkins)],
            "adherence": [c.adherence_percent for c in reversed(checkins)],
        } if checkins else None,
    }


@router.get("/checklist/my")
def my_checklist(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Việc cần làm của hội viên (từ AI, HLV hoặc lễ tân)."""
    member = _member(current_user, db)
    items = (
        db.query(ChecklistItem)
        .filter(ChecklistItem.member_id == member.id)
        .order_by(ChecklistItem.is_done.asc(), ChecklistItem.due_date.asc())
        .limit(50)
        .all()
    )
    return {
        "total": len(items),
        "pending": sum(1 for i in items if not i.is_done),
        "items": [
            {
                "id": i.id,
                "title": i.title,
                "detail": i.detail,
                "source": i.source,
                "due_date": i.due_date,
                "is_done": i.is_done,
                "done_at": i.done_at,
            }
            for i in items
        ],
    }


@router.put("/checklist/{item_id}/done")
def complete_checklist_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đánh dấu hoàn thành một việc."""
    member = _member(current_user, db)
    item = (
        db.query(ChecklistItem)
        .filter(ChecklistItem.id == item_id, ChecklistItem.member_id == member.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy việc này")

    item.is_done = True
    item.done_at = now_local()
    db.commit()

    return {"message": f"Đã hoàn thành: {item.title}", "item_id": item.id}