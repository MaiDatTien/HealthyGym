"""Router PT 1-1, Dashboard Huấn luyện viên, Check-in QR & Bảo trì thiết bị.

Nghiệp vụ:
    - Đặt lịch 1-1 với PT theo khung giờ trống (Real-time Slot).
    - HLV: xem học viên phụ trách, hồ sơ sức khỏe, phác đồ AI, đánh giá sau buổi tập.
    - Hội viên: Check-in điện tử bằng mã QR, xem lịch sử tập với PT.
    - Admin/Staff: quản lý bảo trì thiết bị phòng gym.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai import AIPlan, DailyCheckin, HealthMetric, WorkoutLog
from app.models.interaction import CheckInLog, now_local
from app.models.listing import Branch, Facility
from app.models.pt import CoachNote, EquipmentMaintenance, PTBooking, TrainerSlot
from app.models.trainer_ops import PTBurnConfirmation
from app.models.user import Member, Trainer, User
from app.schemas.ai import (
    CoachNoteCreate,
    MaintenanceCreate,
    MaintenanceResolve,
    PTBookingCreate,
    PTFeedbackInput,
    QRCheckinRequest,
    TrainerSlotCreate,
)
from app.security import (
    get_current_user,
    require_staff_or_admin,
    require_trainer_or_admin,
)

router = APIRouter(prefix="/pt", tags=["PT 1-1, Coach Dashboard & Vận hành"])


def _member(user: User, db: Session) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hội viên")
    return member


def _trainer_of_user(user: User, db: Session) -> Trainer:
    """Xác định hồ sơ HLV gắn với tài khoản đăng nhập."""
    trainer = db.query(Trainer).filter(Trainer.user_id == user.id).first()
    if not trainer:
        # Cho phép admin/staff xem dashboard của HLV đầu tiên
        if user.role in ("admin", "staff"):
            trainer = db.query(Trainer).order_by(Trainer.id.asc()).first()
        if not trainer:
            raise HTTPException(
                status_code=404,
                detail="Tài khoản của bạn chưa được gắn với hồ sơ Huấn luyện viên nào. "
                       "Vui lòng liên hệ Admin để liên kết.",
            )
    return trainer


def member_qr_token(member: Member) -> str:
    """Sinh mã QR định danh hội viên (dạng HG-<id>-<hash ngắn>)."""
    raw = f"healthygym:{member.id}:{member.phone or member.full_name}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10].upper()
    return f"HG-{member.id}-{digest}"


# ==========================================================================
# KHUNG GIỜ TRỐNG CỦA HLV
# ==========================================================================
@router.get("/trainers")
def list_trainers_with_slots(db: Session = Depends(get_db)):
    """Danh sách HLV kèm số khung giờ còn trống và chuyên môn."""
    trainers = db.query(Trainer).order_by(Trainer.id.asc()).all()
    result = []
    now = datetime.now()
    for t in trainers:
        available = (
            db.query(func.count(TrainerSlot.id))
            .filter(
                TrainerSlot.trainer_id == t.id,
                TrainerSlot.is_booked == False,
                TrainerSlot.start_time >= now,
            )
            .scalar()
            or 0
        )
        completed = (
            db.query(func.count(PTBooking.id))
            .filter(PTBooking.trainer_id == t.id, PTBooking.status == "completed")
            .scalar()
            or 0
        )
        rating_rows = (
            db.query(PTBooking.rating)
            .filter(PTBooking.trainer_id == t.id, PTBooking.rating != None)
            .all()
        )
        avg_rating = (
            round(sum(r[0] for r in rating_rows) / len(rating_rows), 1)
            if rating_rows
            else t.rating or 5.0
        )
        result.append({
            "id": t.id,
            "full_name": t.full_name,
            "specialty": t.specialty,
            "bio": t.bio,
            "experience_years": t.experience_years,
            "certifications": t.certifications,
            "branch_id": t.branch_id,
            "branch_name": t.branch.name if hasattr(t, "branch") and t.branch else None,
            "rating": avg_rating,
            "completed_sessions": completed,
            "available_slots": available,
        })
    return result


@router.get("/slots")
def list_slots(
    trainer_id: Optional[int] = None,
    only_available: bool = Query(True, description="Chỉ hiện khung giờ còn trống"),
    days_ahead: int = Query(14, ge=1, le=60),
    db: Session = Depends(get_db),
):
    """Khung giờ tập 1-1 (Real-time Slot) cho hội viên chọn."""
    now = datetime.now()
    until = now + timedelta(days=days_ahead)
    query = db.query(TrainerSlot).filter(
        TrainerSlot.start_time >= now, TrainerSlot.start_time <= until
    )
    if trainer_id:
        query = query.filter(TrainerSlot.trainer_id == trainer_id)
    if only_available:
        query = query.filter(TrainerSlot.is_booked == False)

    slots = query.order_by(TrainerSlot.start_time.asc()).limit(200).all()
    return [
        {
            "id": s.id,
            "trainer_id": s.trainer_id,
            "trainer_name": s.trainer.full_name if s.trainer else "HLV",
            "trainer_specialty": s.trainer.specialty if s.trainer else "",
            "branch_id": s.branch_id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "duration_minutes": int((s.end_time - s.start_time).total_seconds() // 60),
            "is_booked": s.is_booked,
            "note": s.note,
            "session_date": s.start_time.date(),
            "time_label": s.start_time.strftime("%H:%M"),
        }
        for s in slots
    ]


@router.post("/slots")
def create_slot(
    data: TrainerSlotCreate,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Admin/PT mở khung giờ dạy 1-1."""
    if data.end_time <= data.start_time:
        raise HTTPException(status_code=422, detail="Giờ kết thúc phải sau giờ bắt đầu")
    if not db.query(Trainer).filter(Trainer.id == data.trainer_id).first():
        raise HTTPException(status_code=404, detail="Không tìm thấy Huấn luyện viên")

    slot = TrainerSlot(**data.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return {"message": "Đã mở khung giờ dạy", "slot_id": slot.id}


@router.delete("/slots/{slot_id}")
def delete_slot(
    slot_id: int,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    slot = db.query(TrainerSlot).filter(TrainerSlot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Không tìm thấy khung giờ")
    if slot.is_booked:
        raise HTTPException(
            status_code=400,
            detail="Khung giờ đã có hội viên đặt. Hãy hủy lịch đặt trước khi xóa.",
        )
    db.delete(slot)
    db.commit()
    return {"message": "Đã xóa khung giờ"}


# ==========================================================================
# ĐẶT LỊCH 1-1
# ==========================================================================
@router.post("/bookings")
def book_pt_session(
    data: PTBookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hội viên đặt lịch tập 1-1 với PT theo khung giờ trống."""
    member = _member(current_user, db)
    today = date.today()

    if member.frozen_until and member.frozen_until >= today:
        raise HTTPException(
            status_code=400,
            detail=f"Thẻ tập đang bảo lưu đến {member.frozen_until}. "
                   f"Vui lòng mở khóa thẻ trước khi đặt lịch 1-1.",
        )
    if not member.expire_date or member.expire_date < today or member.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Thẻ hội viên chưa kích hoạt hoặc đã hết hạn. "
                   "Vui lòng gia hạn gói tập trước khi đặt lịch với PT.",
        )

    # Khóa khung giờ để tránh 2 hội viên đặt cùng lúc (Real-time Slot)
    slot = (
        db.query(TrainerSlot)
        .filter(TrainerSlot.id == data.slot_id)
        .with_for_update()
        .first()
    )
    if not slot:
        raise HTTPException(status_code=404, detail="Không tìm thấy khung giờ này")
    if slot.is_booked:
        raise HTTPException(
            status_code=409,
            detail="Khung giờ này vừa được hội viên khác đặt. "
                   "Vui lòng chọn khung giờ khác.",
        )
    if slot.start_time < datetime.now():
        raise HTTPException(status_code=400, detail="Khung giờ này đã qua, không thể đặt")

    booking = PTBooking(
        member_id=member.id,
        trainer_id=slot.trainer_id,
        slot_id=slot.id,
        status="confirmed",
        goal_note=data.goal_note,
    )
    slot.is_booked = True
    db.add(booking)

    # Gán HLV phụ trách cho hội viên nếu chưa có
    if not member.trainer_id:
        member.trainer_id = slot.trainer_id

    db.commit()
    db.refresh(booking)

    return {
        "message": f"Đặt lịch 1-1 thành công với {slot.trainer.full_name} "
                   f"lúc {slot.start_time.strftime('%H:%M ngày %d/%m/%Y')}",
        "booking_id": booking.id,
        "trainer_name": slot.trainer.full_name,
        "start_time": slot.start_time,
        "end_time": slot.end_time,
    }


@router.get("/bookings/my")
def my_pt_bookings(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Lịch tập 1-1 của hội viên."""
    member = _member(current_user, db)
    items = (
        db.query(PTBooking)
        .filter(PTBooking.member_id == member.id)
        .order_by(PTBooking.created_at.desc())
        .all()
    )

    # Trạng thái xác nhận kép (chống gian lận) để hội viên biết buổi nào cần xác nhận
    booking_ids = [b.id for b in items]
    confirmations = (
        db.query(PTBurnConfirmation)
        .filter(PTBurnConfirmation.booking_id.in_(booking_ids))
        .all()
        if booking_ids else []
    )
    burn_by_booking = {c.booking_id: c for c in confirmations}

    return [
        {
            "id": b.id,
            "trainer_name": b.trainer.full_name if b.trainer else "HLV",
            "trainer_specialty": b.trainer.specialty if b.trainer else "",
            "start_time": b.slot.start_time if b.slot else None,
            "end_time": b.slot.end_time if b.slot else None,
            "status": b.status,
            "goal_note": b.goal_note,
            "trainer_feedback": b.trainer_feedback,
            "rating": b.rating,
            # --- Xác nhận kép ---
            "trainer_marked_complete": b.id in burn_by_booking,
            "member_checked_in": (
                burn_by_booking[b.id].member_checked_in if b.id in burn_by_booking else False
            ),
            "member_confirmed": (
                burn_by_booking[b.id].member_confirmed if b.id in burn_by_booking else False
            ),
            "session_deducted": (
                burn_by_booking[b.id].session_deducted if b.id in burn_by_booking else False
            ),
            "needs_confirmation": (
                b.id in burn_by_booking
                and not burn_by_booking[b.id].session_deducted
                and not burn_by_booking[b.id].member_confirmed
            ),
        }
        for b in items
    ]


@router.post("/bookings/{booking_id}/cancel")
def cancel_pt_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hủy lịch 1-1 và giải phóng khung giờ (chỉ trước 12 giờ)."""
    member = _member(current_user, db)
    booking = (
        db.query(PTBooking)
        .filter(PTBooking.id == booking_id, PTBooking.member_id == member.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch đặt")

    if booking.slot and booking.slot.start_time - datetime.now() < timedelta(hours=12):
        raise HTTPException(
            status_code=400,
            detail="Chỉ được hủy lịch trước giờ tập ít nhất 12 giờ. "
                   "Vui lòng liên hệ trực tiếp phòng tập để được hỗ trợ.",
        )

    booking.status = "cancelled"
    if booking.slot:
        booking.slot.is_booked = False
    db.commit()
    return {"message": "Đã hủy lịch tập 1-1 và giải phóng khung giờ"}


@router.post("/bookings/{booking_id}/feedback")
def pt_feedback(
    booking_id: int,
    data: PTFeedbackInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hội viên đánh giá buổi tập với PT."""
    member = _member(current_user, db)
    booking = (
        db.query(PTBooking)
        .filter(PTBooking.id == booking_id, PTBooking.member_id == member.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch đặt")

    booking.rating = data.rating
    if data.feedback:
        booking.goal_note = (
            f"{booking.goal_note or ''}\n[Đánh giá của hội viên]: {data.feedback}".strip()
        )
    db.commit()
    return {"message": "Cảm ơn bạn đã đánh giá buổi tập!"}


# ==========================================================================
# DASHBOARD HUẤN LUYỆN VIÊN
# ==========================================================================
@router.get("/coach/overview")
def coach_overview(
    current_user: User = Depends(require_trainer_or_admin), db: Session = Depends(get_db)
):
    """Tổng quan của HLV: lịch dạy, số học viên, đánh giá."""
    trainer = _trainer_of_user(current_user, db)
    now = datetime.now()
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)

    trainees = db.query(Member).filter(Member.trainer_id == trainer.id).all()
    today_sessions = (
        db.query(PTBooking)
        .join(TrainerSlot, PTBooking.slot_id == TrainerSlot.id)
        .filter(
            PTBooking.trainer_id == trainer.id,
            TrainerSlot.start_time >= today_start,
            TrainerSlot.start_time < today_end,
            PTBooking.status.in_(["confirmed", "completed"]),
        )
        .order_by(TrainerSlot.start_time.asc())
        .all()
    )
    upcoming = (
        db.query(PTBooking)
        .join(TrainerSlot, PTBooking.slot_id == TrainerSlot.id)
        .filter(
            PTBooking.trainer_id == trainer.id,
            TrainerSlot.start_time >= now,
            PTBooking.status == "confirmed",
        )
        .order_by(TrainerSlot.start_time.asc())
        .limit(10)
        .all()
    )
    classes_taught = (
        db.query(func.count()).select_from(
            db.query(TrainerSlot).filter(TrainerSlot.trainer_id == trainer.id).subquery()
        ).scalar()
        or 0
    )
    pending_notes = (
        db.query(func.count(PTBooking.id))
        .filter(PTBooking.trainer_id == trainer.id, PTBooking.status == "confirmed")
        .scalar()
        or 0
    )

    return {
        "trainer": {
            "id": trainer.id,
            "full_name": trainer.full_name,
            "specialty": trainer.specialty,
            "experience_years": trainer.experience_years,
            "certifications": trainer.certifications,
        },
        "stats": {
            "total_trainees": len(trainees),
            "sessions_today": len(today_sessions),
            "upcoming_sessions": len(upcoming),
            "total_slots_opened": classes_taught,
            "sessions_awaiting_feedback": pending_notes,
        },
        "today_schedule": [
            {
                "booking_id": b.id,
                "member_id": b.member_id,
                "member_name": b.member.full_name if b.member else "",
                "start_time": b.slot.start_time,
                "end_time": b.slot.end_time,
                "status": b.status,
                "goal_note": b.goal_note,
            }
            for b in today_sessions
        ],
        "upcoming_sessions": [
            {
                "booking_id": b.id,
                "member_name": b.member.full_name if b.member else "",
                "start_time": b.slot.start_time,
                "status": b.status,
            }
            for b in upcoming
        ],
    }


@router.get("/coach/trainees")
def coach_trainees(
    current_user: User = Depends(require_trainer_or_admin), db: Session = Depends(get_db)
):
    """Danh sách học viên HLV đang phụ trách, kèm chỉ số mới nhất và phác đồ AI."""
    trainer = _trainer_of_user(current_user, db)
    trainees = db.query(Member).filter(Member.trainer_id == trainer.id).all()

    result = []
    for m in trainees:
        latest_metric = (
            db.query(HealthMetric)
            .filter(HealthMetric.member_id == m.id)
            .order_by(HealthMetric.measured_at.desc(), HealthMetric.id.desc())
            .first()
        )
        active_plan = (
            db.query(AIPlan)
            .filter(AIPlan.member_id == m.id, AIPlan.is_active == True)
            .order_by(AIPlan.created_at.desc())
            .first()
        )
        last_workout = (
            db.query(WorkoutLog)
            .filter(WorkoutLog.member_id == m.id)
            .order_by(WorkoutLog.log_date.desc())
            .first()
        )
        result.append({
            "member_id": m.id,
            "full_name": m.full_name,
            "phone": m.phone,
            "status": m.status,
            "expire_date": m.expire_date,
            "latest_metric": {
                "measured_at": latest_metric.measured_at,
                "weight_kg": latest_metric.weight_kg,
                "body_fat_percentage": latest_metric.body_fat_percentage,
                "bmi": latest_metric.bmi,
                "body_type": latest_metric.body_type_classification,
                "tdee_kcal": latest_metric.tdee_kcal,
            }
            if latest_metric
            else None,
            "ai_plan": {
                "plan_id": active_plan.id,
                "goal": active_plan.goal,
                "split_type": active_plan.split_type,
                "target_daily_calories": active_plan.target_daily_calories,
                "protein_grams": active_plan.protein_grams,
                "training_days_per_week": active_plan.training_days_per_week,
                "injuries": active_plan.injuries,
                "allergies": active_plan.allergies,
            }
            if active_plan
            else None,
            "last_workout_date": last_workout.log_date if last_workout else None,
        })
    return result


@router.get("/coach/trainees/{member_id}")
def coach_trainee_detail(
    member_id: int,
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """Hồ sơ sức khỏe chi tiết + phác đồ AI của một học viên."""
    trainer = _trainer_of_user(current_user, db)
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")

    metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.member_id == member.id)
        .order_by(HealthMetric.measured_at.asc())
        .all()
    )
    active_plan = (
        db.query(AIPlan)
        .filter(AIPlan.member_id == member.id, AIPlan.is_active == True)
        .order_by(AIPlan.created_at.desc())
        .first()
    )
    notes = (
        db.query(CoachNote)
        .filter(CoachNote.member_id == member.id)
        .order_by(CoachNote.note_date.desc())
        .limit(20)
        .all()
    )
    recent_workouts = (
        db.query(WorkoutLog)
        .filter(WorkoutLog.member_id == member.id)
        .order_by(WorkoutLog.log_date.desc())
        .limit(30)
        .all()
    )

    return {
        "member": {
            "id": member.id,
            "full_name": member.full_name,
            "phone": member.phone,
            "email": member.email,
            "status": member.status,
            "join_date": member.join_date,
            "expire_date": member.expire_date,
        },
        "metrics_history": [
            {
                "measured_at": m.measured_at,
                "weight_kg": m.weight_kg,
                "body_fat_percentage": m.body_fat_percentage,
                "muscle_mass_kg": m.muscle_mass_kg or m.lean_body_mass_kg,
                "bmi": m.bmi,
                "tdee_kcal": m.tdee_kcal,
                "body_type": m.body_type_classification,
                "source": m.source,
            }
            for m in metrics
        ],
        "ai_plan": {
            "plan_id": active_plan.id,
            "goal": active_plan.goal,
            "split_type": active_plan.split_type,
            "target_daily_calories": active_plan.target_daily_calories,
            "macros": {
                "protein_grams": active_plan.protein_grams,
                "carbs_grams": active_plan.carbs_grams,
                "fat_grams": active_plan.fat_grams,
            },
            "injuries": active_plan.injuries,
            "allergies": active_plan.allergies,
            "summary_text": active_plan.summary_text,
            "diagnosis": json.loads(active_plan.diagnosis_json)
            if active_plan.diagnosis_json
            else None,
            "workout_schedule": json.loads(active_plan.workout_json)
            if active_plan.workout_json
            else None,
            "nutrition_plan": json.loads(active_plan.nutrition_json)
            if active_plan.nutrition_json
            else None,
        }
        if active_plan
        else None,
        "coach_notes": [
            {
                "id": n.id,
                "note_date": n.note_date,
                "performance": n.performance,
                "content": n.content,
                "next_focus": n.next_focus,
            }
            for n in notes
        ],
        "recent_workouts": [
            {
                "log_date": w.log_date,
                "exercise_name": w.exercise_name,
                "sets": w.sets,
                "reps": w.reps,
                "weight_kg": w.weight_kg,
                "rpe": w.rpe,
            }
            for w in recent_workouts
        ],
        "is_my_trainee": member.trainer_id == trainer.id,
    }


@router.post("/coach/notes")
def add_coach_note(
    data: CoachNoteCreate,
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """HLV ghi đánh giá sau buổi tập cho học viên."""
    trainer = _trainer_of_user(current_user, db)
    if not db.query(Member).filter(Member.id == data.member_id).first():
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")

    note = CoachNote(
        trainer_id=trainer.id,
        member_id=data.member_id,
        performance=data.performance,
        content=data.content,
        next_focus=data.next_focus,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"message": "Đã lưu đánh giá cho học viên", "note_id": note.id}


@router.post("/coach/bookings/{booking_id}/complete")
def complete_session(
    booking_id: int,
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """HLV đánh dấu hoàn thành buổi tập 1-1."""
    trainer = _trainer_of_user(current_user, db)
    booking = (
        db.query(PTBooking)
        .filter(PTBooking.id == booking_id, PTBooking.trainer_id == trainer.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi tập")

    booking.status = "completed"
    db.commit()
    return {"message": "Đã đánh dấu hoàn thành buổi tập"}


# ==========================================================================
# CHECK-IN QR ĐIỆN TỬ
# ==========================================================================
@router.get("/checkin/qr")
def get_my_qr(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Lấy mã QR check-in của hội viên."""
    member = _member(current_user, db)
    today = date.today()

    can_checkin = True
    reason = None
    if member.frozen_until and member.frozen_until >= today:
        can_checkin, reason = False, f"Thẻ đang bảo lưu đến {member.frozen_until}"
    elif not member.expire_date or member.expire_date < today:
        can_checkin, reason = False, "Thẻ đã hết hạn hoặc chưa kích hoạt"

    recent = (
        db.query(CheckInLog)
        .filter(CheckInLog.member_id == member.id)
        .order_by(CheckInLog.checkin_time.desc())
        .limit(10)
        .all()
    )

    return {
        "qr_code": member_qr_token(member),
        "member_id": member.id,
        "member_name": member.full_name,
        "plan_name": member.current_plan.name if member.current_plan else "Chưa có gói",
        "status": member.status,
        "expire_date": member.expire_date,
        "can_checkin": can_checkin,
        "reason": reason,
        "recent_checkins": [
            {
                "checkin_time": c.checkin_time,
                "checked_by": c.checked_by,
            }
            for c in recent
        ],
    }


@router.post("/checkin/scan")
def scan_qr_checkin(
    data: QRCheckinRequest,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Quét mã QR của hội viên để check-in (Staff/Admin hoặc máy quét tại quầy)."""
    code = data.qr_code.strip().upper()
    parts = code.split("-")
    if len(parts) < 3 or parts[0] != "HG":
        raise HTTPException(
            status_code=400,
            detail="Mã QR không hợp lệ. Định dạng đúng: HG-<mã hội viên>-<mã xác thực>",
        )

    try:
        member_id = int(parts[1])
    except ValueError:
        raise HTTPException(status_code=400, detail="Mã QR không hợp lệ")

    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên với mã QR này")

    if member_qr_token(member) != code:
        raise HTTPException(
            status_code=400,
            detail="Mã QR không khớp với hồ sơ hội viên. Vui lòng kiểm tra lại.",
        )

    today = date.today()
    if member.frozen_until and member.frozen_until >= today:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể check-in: Thẻ đang bảo lưu đến {member.frozen_until}",
        )
    if not member.expire_date or member.expire_date < today:
        raise HTTPException(
            status_code=400,
            detail="Không thể check-in: Thẻ đã hết hạn hoặc chưa mua gói tập",
        )

    # Chống check-in trùng trong vòng 30 phút
    recent = (
        db.query(CheckInLog)
        .filter(
            CheckInLog.member_id == member.id,
            CheckInLog.checkin_time >= datetime.now() - timedelta(minutes=30),
        )
        .first()
    )
    if recent:
        return {
            "message": f"Hội viên {member.full_name} đã check-in lúc "
                       f"{recent.checkin_time.strftime('%H:%M')} (cách đây chưa đầy 30 phút).",
            "duplicate": True,
            "member_name": member.full_name,
        }

    log = CheckInLog(
        member_id=member.id,
        branch_id=data.branch_id,
        checked_by=f"QR-{current_user.username}",
    )
    db.add(log)
    db.commit()

    return {
        "message": f"Check-in thành công! Chúc {member.full_name} buổi tập hiệu quả.",
        "duplicate": False,
        "member_name": member.full_name,
        "plan_name": member.current_plan.name if member.current_plan else None,
        "expire_date": member.expire_date,
        "checkin_time": log.checkin_time,
    }


# ==========================================================================
# BẢO TRÌ THIẾT BỊ & VẬN HÀNH
# ==========================================================================
@router.get("/equipment")
def list_equipment(
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Danh sách thiết bị kèm tình trạng và phiếu bảo trì đang mở."""
    query = db.query(Facility)
    if branch_id:
        query = query.filter(Facility.branch_id == branch_id)
    facilities = query.order_by(Facility.id.asc()).all()

    result = []
    for f in facilities:
        open_tickets = (
            db.query(func.count(EquipmentMaintenance.id))
            .filter(
                EquipmentMaintenance.facility_id == f.id,
                EquipmentMaintenance.status != "resolved",
            )
            .scalar()
            or 0
        )
        if status and f.status != status:
            continue
        result.append({
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "quantity": f.quantity,
            "status": f.status,
            "description": f.description,
            "branch_id": f.branch_id,
            "open_maintenance_tickets": open_tickets,
        })
    return result


@router.get("/maintenance")
def list_maintenance(
    status: Optional[str] = Query(None, description="pending|in_progress|resolved"),
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Danh sách phiếu bảo trì / sự cố thiết bị."""
    query = db.query(EquipmentMaintenance)
    if status:
        query = query.filter(EquipmentMaintenance.status == status)
    tickets = query.order_by(EquipmentMaintenance.reported_at.desc()).limit(100).all()
    return [
        {
            "id": t.id,
            "facility_id": t.facility_id,
            "facility_name": t.facility.name if t.facility else "",
            "issue": t.issue,
            "severity": t.severity,
            "status": t.status,
            "reported_by": t.reported_by,
            "technician": t.technician,
            "cost": t.cost,
            "reported_at": t.reported_at,
            "resolved_at": t.resolved_at,
        }
        for t in tickets
    ]


@router.post("/maintenance")
def create_maintenance(
    data: MaintenanceCreate,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Báo cáo sự cố thiết bị và tạo phiếu bảo trì."""
    facility = db.query(Facility).filter(Facility.id == data.facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    ticket = EquipmentMaintenance(
        facility_id=data.facility_id,
        issue=data.issue,
        severity=data.severity,
        reported_by=current_user.full_name or current_user.username,
        technician=data.technician,
        cost=data.cost,
        status="pending",
    )
    db.add(ticket)

    # Thiết bị nặng/hỏng -> cập nhật trạng thái để hội viên thấy
    if data.severity in ("high", "medium"):
        facility.status = "Đang bảo trì"

    db.commit()
    db.refresh(ticket)
    return {
        "message": f"Đã tạo phiếu bảo trì cho '{facility.name}'",
        "ticket_id": ticket.id,
    }


@router.put("/maintenance/{ticket_id}")
def update_maintenance(
    ticket_id: int,
    data: MaintenanceResolve,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Cập nhật trạng thái phiếu bảo trì."""
    ticket = (
        db.query(EquipmentMaintenance)
        .filter(EquipmentMaintenance.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu bảo trì")

    ticket.status = data.status
    if data.technician:
        ticket.technician = data.technician
    if data.cost is not None:
        ticket.cost = data.cost

    if data.status == "resolved":
        ticket.resolved_at = now_local()
        facility = db.query(Facility).filter(Facility.id == ticket.facility_id).first()
        if facility:
            still_open = (
                db.query(func.count(EquipmentMaintenance.id))
                .filter(
                    EquipmentMaintenance.facility_id == facility.id,
                    EquipmentMaintenance.status != "resolved",
                    EquipmentMaintenance.id != ticket.id,
                )
                .scalar()
                or 0
            )
            if still_open == 0:
                facility.status = "Hoạt động tốt"

    db.commit()
    return {"message": f"Đã cập nhật phiếu bảo trì sang trạng thái '{data.status}'"}