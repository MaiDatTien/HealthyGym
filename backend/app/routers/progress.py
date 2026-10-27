"""Router Theo dõi Tiến độ (Progress Tracker) & Nhật ký tập luyện.

Nghiệp vụ:
    - Ghi nhận chỉ số cơ thể theo thời gian (InBody / nhập tay / AI Coach).
    - Biểu đồ Cân nặng, % Body Fat, Khối lượng cơ qua từng tuần.
    - Nhật ký tập luyện (Progressive Overload) và Nhật ký Calo.
    - Thống kê tuân thủ & so sánh với mục tiêu trong phác đồ AI.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai import AIPlan, DailyCheckin, HealthMetric, WorkoutLog
from app.models.user import Member, User
from app.schemas.ai import DailyCheckinCreate, HealthMetricCreate, WorkoutLogCreate
from app.security import get_current_user
from app.services.ai_diagnosis import run_full_diagnosis

router = APIRouter(prefix="/progress", tags=["Progress Tracker & Nhật ký"])


def _member(user: User, db: Session) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hội viên")
    return member


# --------------------------------------------------------------------------
# CHỈ SỐ CƠ THỂ
# --------------------------------------------------------------------------
@router.post("/metrics")
def add_metric(
    data: HealthMetricCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ghi nhận một lần đo chỉ số cơ thể (InBody hoặc nhập tay)."""
    member = _member(current_user, db)

    # Nếu chưa có Body Fat % thì thử ước tính từ số đo vòng
    body_fat = data.body_fat_percentage
    if body_fat is None and data.neck_cm and data.waist_cm:
        from app.services.ai_diagnosis import estimate_body_fat_us_navy

        try:
            body_fat = estimate_body_fat_us_navy(
                gender=data.gender or "male",
                height_cm=data.height_cm,
                neck_cm=data.neck_cm,
                waist_cm=data.waist_cm,
                hip_cm=data.hip_cm,
            )
        except ValueError:
            body_fat = None

    if body_fat is None:
        raise HTTPException(
            status_code=422,
            detail="Cần cung cấp 'body_fat_percentage', hoặc đủ số đo "
                   "'neck_cm' + 'waist_cm' để hệ thống tự ước tính.",
        )

    diagnosis = run_full_diagnosis(
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        body_fat_percentage=body_fat,
        gender=data.gender or "male",
        age=data.age,
        activity_level="moderate",
    )

    metric = HealthMetric(
        member_id=member.id,
        measured_at=data.measured_at or date.today(),
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        body_fat_percentage=body_fat,
        age=data.age,
        gender=data.gender or "male",
        muscle_mass_kg=data.muscle_mass_kg or diagnosis.lean_body_mass_kg,
        visceral_fat_level=data.visceral_fat_level,
        waist_cm=data.waist_cm,
        neck_cm=data.neck_cm,
        hip_cm=data.hip_cm,
        body_water_kg=data.body_water_kg,
        bmi=diagnosis.bmi,
        lean_body_mass_kg=diagnosis.lean_body_mass_kg,
        fat_mass_kg=diagnosis.fat_mass_kg,
        bmr_kcal=diagnosis.bmr_kcal,
        tdee_kcal=diagnosis.tdee_kcal,
        body_type_classification=diagnosis.body_type_vi,
        source=data.source,
        note=data.note,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return {
        "message": f"Đã ghi nhận chỉ số ngày {metric.measured_at}",
        "metric_id": metric.id,
        "bmi": metric.bmi,
        "lean_body_mass_kg": metric.lean_body_mass_kg,
        "body_type": metric.body_type_classification,
    }


@router.get("/metrics")
def list_metrics(
    limit: int = Query(90, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Danh sách chỉ số cơ thể theo thời gian (mới nhất trước)."""
    member = _member(current_user, db)
    items = (
        db.query(HealthMetric)
        .filter(HealthMetric.member_id == member.id)
        .order_by(HealthMetric.measured_at.desc(), HealthMetric.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": m.id,
            "measured_at": m.measured_at,
            "height_cm": m.height_cm,
            "weight_kg": m.weight_kg,
            "body_fat_percentage": m.body_fat_percentage,
            "muscle_mass_kg": m.muscle_mass_kg,
            "lean_body_mass_kg": m.lean_body_mass_kg,
            "fat_mass_kg": m.fat_mass_kg,
            "bmi": m.bmi,
            "bmr_kcal": m.bmr_kcal,
            "tdee_kcal": m.tdee_kcal,
            "visceral_fat_level": m.visceral_fat_level,
            "waist_cm": m.waist_cm,
            "body_type": m.body_type_classification,
            "source": m.source,
            "note": m.note,
        }
        for m in items
    ]


@router.get("/charts")
def progress_charts(
    days: int = Query(180, ge=7, le=730, description="Khoảng thời gian theo ngày"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dữ liệu biểu đồ tiến độ: Cân nặng, % Body Fat, Khối lượng cơ, BMI."""
    member = _member(current_user, db)
    since = date.today() - timedelta(days=days)

    items = (
        db.query(HealthMetric)
        .filter(HealthMetric.member_id == member.id, HealthMetric.measured_at >= since)
        .order_by(HealthMetric.measured_at.asc())
        .all()
    )

    labels = [str(m.measured_at) for m in items]
    series = {
        "weight_kg": [m.weight_kg for m in items],
        "body_fat_percentage": [m.body_fat_percentage for m in items],
        "muscle_mass_kg": [m.muscle_mass_kg or m.lean_body_mass_kg for m in items],
        "lean_body_mass_kg": [m.lean_body_mass_kg for m in items],
        "fat_mass_kg": [m.fat_mass_kg for m in items],
        "bmi": [m.bmi for m in items],
    }

    # Tính mức thay đổi so với lần đo đầu tiên trong khoảng
    delta: dict = {}
    if len(items) >= 2:
        first, last = items[0], items[-1]
        delta = {
            "weight_kg": round((last.weight_kg or 0) - (first.weight_kg or 0), 2),
            "body_fat_percentage": round(
                (last.body_fat_percentage or 0) - (first.body_fat_percentage or 0), 2
            ),
            "muscle_mass_kg": round(
                (last.muscle_mass_kg or last.lean_body_mass_kg or 0)
                - (first.muscle_mass_kg or first.lean_body_mass_kg or 0),
                2,
            ),
            "fat_mass_kg": round((last.fat_mass_kg or 0) - (first.fat_mass_kg or 0), 2),
        }

    # Mục tiêu từ phác đồ AI đang áp dụng
    target: dict = {}
    active_plan = (
        db.query(AIPlan)
        .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
        .order_by(AIPlan.created_at.desc())
        .first()
    )
    if active_plan:
        diag = json.loads(active_plan.diagnosis_json) if active_plan.diagnosis_json else {}
        target = {
            "plan_id": active_plan.id,
            "target_body_fat_percentage": diag.get("target_body_fat_percentage"),
            "fat_to_lose_kg": diag.get("fat_to_lose_kg"),
            "target_daily_calories": active_plan.target_daily_calories,
            "protein_grams": active_plan.protein_grams,
            "estimated_weeks_to_goal": active_plan.estimated_weeks_to_goal,
            "started_at": active_plan.created_at,
        }

    return {
        "labels": labels,
        "series": series,
        "delta": delta,
        "total_records": len(items),
        "target": target or None,
        "motivation": _motivation(delta),
    }


def _motivation(delta: dict) -> str:
    """Sinh câu động viên dựa trên thay đổi thực tế."""
    if not delta:
        return "Hãy ghi nhận chỉ số định kỳ mỗi 1-2 tuần để theo dõi tiến độ rõ ràng."

    fat = delta.get("fat_mass_kg", 0) or 0
    muscle = delta.get("muscle_mass_kg", 0) or 0
    weight = delta.get("weight_kg", 0) or 0

    parts: list[str] = []
    if fat <= -0.5 and muscle >= 0:
        parts.append(
            f"Xuất sắc! Bạn đã giảm {abs(fat)}kg mỡ trong khi vẫn giữ hoặc tăng được cơ. "
            f"Đây chính xác là kết quả mà mọi phác đồ hướng tới."
        )
    elif fat <= -0.5 and muscle < -0.3:
        parts.append(
            f"Bạn đã giảm {abs(fat)}kg mỡ nhưng cũng mất {abs(muscle)}kg cơ. "
            f"Hãy kiểm tra lại lượng đạm nạp vào và đảm bảo vẫn tập tạ nặng, "
            f"không cắt calo quá sâu."
        )
    elif fat >= 0.5 and muscle >= 0.5:
        parts.append(
            f"Bạn đã tăng {muscle}kg cơ và {fat}kg mỡ — đây là giai đoạn tăng cơ bình thường. "
            f"Nếu muốn siết nét hơn, hãy giảm nhẹ 200 kcal/ngày."
        )
    elif weight < -0.3:
        parts.append(f"Tiến độ tốt: bạn đã giảm {abs(weight)}kg. Hãy duy trì đều đặn.")
    elif weight > 0.3:
        parts.append(
            f"Cân nặng tăng {weight}kg. Nếu mục tiêu là giảm mỡ, hãy rà soát lại khẩu phần "
            f"và tăng hoạt động NEAT hằng ngày."
        )
    else:
        parts.append("Chỉ số đang ổn định. Hãy tiếp tục duy trì sự nhất quán.")

    return " ".join(parts)


@router.get("/summary")
def progress_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Tổng quan tiến độ: chỉ số mới nhất, thay đổi, mức tuân thủ nhật ký."""
    member = _member(current_user, db)

    latest = (
        db.query(HealthMetric)
        .filter(HealthMetric.member_id == member.id)
        .order_by(HealthMetric.measured_at.desc(), HealthMetric.id.desc())
        .first()
    )
    first = (
        db.query(HealthMetric)
        .filter(HealthMetric.member_id == member.id)
        .order_by(HealthMetric.measured_at.asc(), HealthMetric.id.asc())
        .first()
    )

    # Tổng hợp nhật ký 30 ngày gần nhất
    since = date.today() - timedelta(days=30)
    checkins = (
        db.query(DailyCheckin)
        .filter(DailyCheckin.member_id == member.id, DailyCheckin.log_date >= since)
        .all()
    )
    workouts = (
        db.query(WorkoutLog)
        .filter(WorkoutLog.member_id == member.id, WorkoutLog.log_date >= since)
        .all()
    )

    avg_calories = (
        round(sum(c.calories_in or 0 for c in checkins) / len(checkins)) if checkins else 0
    )
    avg_protein = (
        round(sum(c.protein_g or 0 for c in checkins) / len(checkins)) if checkins else 0
    )
    avg_water = (
        round(sum(c.water_liters or 0 for c in checkins) / len(checkins), 2)
        if checkins
        else 0
    )
    avg_sleep = (
        round(sum(c.sleep_hours or 0 for c in checkins) / len(checkins), 1)
        if checkins
        else 0
    )
    avg_steps = (
        round(sum(c.steps or 0 for c in checkins) / len(checkins)) if checkins else 0
    )
    workout_minutes = sum(w.duration_minutes or 0 for w in workouts)

    active_plan = (
        db.query(AIPlan)
        .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
        .order_by(AIPlan.created_at.desc())
        .first()
    )

    return {
        "latest_metric": {
            "measured_at": latest.measured_at,
            "weight_kg": latest.weight_kg,
            "body_fat_percentage": latest.body_fat_percentage,
            "muscle_mass_kg": latest.muscle_mass_kg or latest.lean_body_mass_kg,
            "bmi": latest.bmi,
            "tdee_kcal": latest.tdee_kcal,
            "body_type": latest.body_type_classification,
        }
        if latest
        else None,
        "start_metric": {
            "measured_at": first.measured_at,
            "weight_kg": first.weight_kg,
            "body_fat_percentage": first.body_fat_percentage,
        }
        if first
        else None,
        "total_change": {
            "weight_kg": round((latest.weight_kg or 0) - (first.weight_kg or 0), 2)
            if latest and first and latest.id != first.id
            else 0,
            "body_fat_percentage": round(
                (latest.body_fat_percentage or 0) - (first.body_fat_percentage or 0), 2
            )
            if latest and first and latest.id != first.id
            else 0,
        },
        "last_30_days": {
            "checkin_days": len(checkins),
            "avg_calories_in": avg_calories,
            "avg_protein_g": avg_protein,
            "avg_water_liters": avg_water,
            "avg_sleep_hours": avg_sleep,
            "avg_steps": avg_steps,
            "workout_sessions_logged": len({w.log_date for w in workouts}),
            "total_workout_minutes": workout_minutes,
        },
        "active_target": {
            "target_daily_calories": active_plan.target_daily_calories,
            "protein_grams": active_plan.protein_grams,
            "daily_water_liters": active_plan.daily_water_liters,
            "training_days_per_week": active_plan.training_days_per_week,
        }
        if active_plan
        else None,
    }


# --------------------------------------------------------------------------
# NHẬT KÝ TẬP LUYỆN (PROGRESSIVE OVERLOAD)
# --------------------------------------------------------------------------
@router.post("/workout-logs")
def add_workout_log(
    data: WorkoutLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ghi nhật ký một hiệp tập — dữ liệu cho Progressive Overload."""
    member = _member(current_user, db)

    active_plan = (
        db.query(AIPlan)
        .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
        .order_by(AIPlan.created_at.desc())
        .first()
    )

    log = WorkoutLog(
        member_id=member.id,
        ai_plan_id=active_plan.id if active_plan else None,
        log_date=data.log_date or date.today(),
        session_focus=data.session_focus,
        exercise_name=data.exercise_name,
        target_muscle=data.target_muscle,
        sets=data.sets,
        reps=data.reps,
        weight_kg=data.weight_kg,
        rpe=data.rpe,
        duration_minutes=data.duration_minutes,
        calories_burned=data.calories_burned,
        notes=data.notes,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # So sánh với lần tập trước cùng bài để gợi ý Progressive Overload
    previous = (
        db.query(WorkoutLog)
        .filter(
            WorkoutLog.member_id == member.id,
            WorkoutLog.exercise_name == data.exercise_name,
            WorkoutLog.id != log.id,
        )
        .order_by(WorkoutLog.log_date.desc(), WorkoutLog.id.desc())
        .first()
    )

    overload_hint = None
    if previous and previous.weight_kg and data.weight_kg:
        diff = round(data.weight_kg - previous.weight_kg, 2)
        prev_volume = (previous.sets or 0) * (previous.reps or 0) * (previous.weight_kg or 0)
        curr_volume = (data.sets or 0) * (data.reps or 0) * (data.weight_kg or 0)
        if curr_volume > prev_volume:
            overload_hint = (
                f"Tăng tiến tốt! Khối lượng tập (Sets x Reps x Tạ) tăng từ "
                f"{round(prev_volume)} lên {round(curr_volume)} — tương đương "
                f"+{round((curr_volume / prev_volume - 1) * 100)}%. Tiếp tục duy trì đà này."
            )
        elif diff > 0:
            overload_hint = (
                f"Bạn đã tăng {diff}kg so với lần trước. Nếu vẫn giữ được số reps, "
                f"đây là dấu hiệu Progressive Overload đang hoạt động tốt."
            )
        else:
            overload_hint = (
                f"Lần trước bạn tập {previous.weight_kg}kg x {previous.reps} reps "
                f"({previous.sets} hiệp). Khi hoàn thành đủ số reps tối đa với kỹ thuật tốt, "
                f"hãy tăng thêm 2.5kg (thân trên) hoặc 5kg (thân dưới) ở buổi kế tiếp."
            )

    return {
        "message": "Đã ghi nhật ký tập luyện",
        "log_id": log.id,
        "previous": {
            "log_date": previous.log_date,
            "sets": previous.sets,
            "reps": previous.reps,
            "weight_kg": previous.weight_kg,
        }
        if previous
        else None,
        "progressive_overload_hint": overload_hint,
    }


@router.get("/workout-logs")
def list_workout_logs(
    limit: int = Query(50, ge=1, le=300),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nhật ký tập luyện gần đây."""
    member = _member(current_user, db)
    logs = (
        db.query(WorkoutLog)
        .filter(WorkoutLog.member_id == member.id)
        .order_by(WorkoutLog.log_date.desc(), WorkoutLog.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": w.id,
            "log_date": w.log_date,
            "session_focus": w.session_focus,
            "exercise_name": w.exercise_name,
            "target_muscle": w.target_muscle,
            "sets": w.sets,
            "reps": w.reps,
            "weight_kg": w.weight_kg,
            "rpe": w.rpe,
            "duration_minutes": w.duration_minutes,
            "volume_kg": round((w.sets or 0) * (w.reps or 0) * (w.weight_kg or 0)),
            "notes": w.notes,
        }
        for w in logs
    ]


@router.get("/workout-logs/personal-records")
def personal_records(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Kỷ lục cá nhân (PR) theo từng bài tập — mức tạ nặng nhất."""
    member = _member(current_user, db)
    logs = (
        db.query(WorkoutLog)
        .filter(WorkoutLog.member_id == member.id, WorkoutLog.weight_kg != None)
        .all()
    )

    records: dict[str, dict] = {}
    for log in logs:
        key = log.exercise_name
        volume = (log.sets or 0) * (log.reps or 0) * (log.weight_kg or 0)
        existing = records.get(key)
        if not existing or (log.weight_kg or 0) > existing["weight_kg"]:
            records[key] = {
                "exercise_name": key,
                "target_muscle": log.target_muscle,
                "weight_kg": log.weight_kg,
                "reps": log.reps,
                "sets": log.sets,
                "volume_kg": round(volume),
                "achieved_on": log.log_date,
            }
        else:
            existing["volume_kg"] = max(existing["volume_kg"], round(volume))

    return sorted(records.values(), key=lambda r: r["weight_kg"], reverse=True)


@router.get("/workout-logs/progress/{exercise_name}")
def exercise_progress(
    exercise_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Biểu đồ tiến bộ mức tạ theo thời gian cho một bài tập cụ thể."""
    member = _member(current_user, db)
    logs = (
        db.query(WorkoutLog)
        .filter(
            WorkoutLog.member_id == member.id,
            WorkoutLog.exercise_name == exercise_name,
        )
        .order_by(WorkoutLog.log_date.asc())
        .all()
    )
    return {
        "exercise_name": exercise_name,
        "labels": [str(w.log_date) for w in logs],
        "weight_kg": [w.weight_kg for w in logs],
        "volume_kg": [round((w.sets or 0) * (w.reps or 0) * (w.weight_kg or 0)) for w in logs],
        "sessions": len(logs),
    }


# --------------------------------------------------------------------------
# NHẬT KÝ DINH DƯỠNG / NƯỚC / GIẤC NGỦ
# --------------------------------------------------------------------------
@router.post("/checkins")
def add_checkin(
    data: DailyCheckinCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ghi nhật ký hằng ngày. Nếu đã có bản ghi cùng ngày thì cập nhật."""
    member = _member(current_user, db)
    log_date = data.log_date or date.today()

    record = (
        db.query(DailyCheckin)
        .filter(DailyCheckin.member_id == member.id, DailyCheckin.log_date == log_date)
        .first()
    )
    created = False
    if not record:
        record = DailyCheckin(member_id=member.id, log_date=log_date)
        db.add(record)
        created = True

    for field, value in data.model_dump(exclude={"log_date"}).items():
        if value is not None:
            setattr(record, field, value)

    db.commit()
    db.refresh(record)

    # Đánh giá mức tuân thủ so với mục tiêu trong phác đồ AI
    active_plan = (
        db.query(AIPlan)
        .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
        .order_by(AIPlan.created_at.desc())
        .first()
    )
    adherence: dict = {}
    if active_plan:
        if record.calories_in is not None and active_plan.target_daily_calories:
            diff = round(record.calories_in - active_plan.target_daily_calories)
            adherence["calories"] = {
                "target": active_plan.target_daily_calories,
                "actual": record.calories_in,
                "difference": diff,
                "status": "Đạt mục tiêu"
                if abs(diff) <= 150
                else ("Vượt mục tiêu" if diff > 0 else "Dưới mục tiêu"),
            }
        if record.protein_g is not None and active_plan.protein_grams:
            pct = round(record.protein_g / active_plan.protein_grams * 100)
            adherence["protein"] = {
                "target": active_plan.protein_grams,
                "actual": record.protein_g,
                "percent": pct,
                "status": "Đủ đạm" if pct >= 90 else f"Còn thiếu {pct}% mục tiêu đạm",
            }
        if record.water_liters is not None and active_plan.daily_water_liters:
            pct = round(record.water_liters / active_plan.daily_water_liters * 100)
            adherence["water"] = {
                "target": active_plan.daily_water_liters,
                "actual": record.water_liters,
                "percent": pct,
                "status": "Đủ nước" if pct >= 90 else f"Cần uống thêm nước ({pct}% mục tiêu)",
            }

    return {
        "message": f"{'Đã ghi' if created else 'Đã cập nhật'} nhật ký ngày {log_date}",
        "checkin_id": record.id,
        "adherence": adherence or None,
    }


@router.get("/checkins")
def list_checkins(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nhật ký dinh dưỡng theo ngày."""
    member = _member(current_user, db)
    since = date.today() - timedelta(days=days)
    items = (
        db.query(DailyCheckin)
        .filter(DailyCheckin.member_id == member.id, DailyCheckin.log_date >= since)
        .order_by(DailyCheckin.log_date.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "log_date": c.log_date,
            "calories_in": c.calories_in,
            "protein_g": c.protein_g,
            "carbs_g": c.carbs_g,
            "fat_g": c.fat_g,
            "water_liters": c.water_liters,
            "sleep_hours": c.sleep_hours,
            "steps": c.steps,
            "weight_kg": c.weight_kg,
            "mood": c.mood,
            "note": c.note,
        }
        for c in items
    ]


@router.get("/checkins/chart")
def checkin_chart(
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dữ liệu biểu đồ nhật ký: calo nạp, đạm, nước, giấc ngủ, bước chân."""
    member = _member(current_user, db)
    since = date.today() - timedelta(days=days)
    items = (
        db.query(DailyCheckin)
        .filter(DailyCheckin.member_id == member.id, DailyCheckin.log_date >= since)
        .order_by(DailyCheckin.log_date.asc())
        .all()
    )
    return {
        "labels": [str(c.log_date) for c in items],
        "series": {
            "calories_in": [c.calories_in for c in items],
            "protein_g": [c.protein_g for c in items],
            "water_liters": [c.water_liters for c in items],
            "sleep_hours": [c.sleep_hours for c in items],
            "steps": [c.steps for c in items],
        },
    }