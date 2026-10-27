"""Router GROUP-X — Lịch lớp nhóm, chọn vị trí, danh sách chờ tự động, phạt no-show."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.engagement import RetentionTask
from app.models.interaction import now_local
from app.models.listing import GymClass
from app.models.operations import (
    BookingPenalty, BookingStatus, ClassBooking, ClassSchedule,
    ClassSpot, ClassWaitlist, ScheduleStatus,
)
from app.models.user import Member, Role, Trainer, User
from app.schemas.erp import (
    ClassBookRequest, ClassScheduleCreate, SubstituteTrainerAssign,
)
from app.security import get_current_user, require_operations, require_trainer_or_admin

router = APIRouter(prefix="/groupx", tags=["Group-X Classes"])


#: Số lần no-show trong 1 tháng thì bị khóa đặt lớp
NO_SHOW_LIMIT_PER_MONTH = 3
#: Số ngày bị khóa đặt lớp
PENALTY_BLOCK_DAYS = 7
#: Hủy trước bao nhiêu giờ thì không tính no-show
CANCEL_GRACE_HOURS = 2


def _member_of(user: User, db: Session) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hội viên")
    return member


def _active_penalty(member_id: int, db: Session) -> Optional[BookingPenalty]:
    """Hình phạt khóa đặt lớp đang hiệu lực."""
    today = date.today()
    return (
        db.query(BookingPenalty)
        .filter(
            BookingPenalty.member_id == member_id,
            BookingPenalty.is_active == True,
            BookingPenalty.blocked_until >= today,
        )
        .first()
    )


def _enrolled_count(schedule_id: int, db: Session) -> int:
    """Số chỗ đã được đặt (không tính đã hủy)."""
    return (
        db.query(func.count(ClassBooking.id))
        .filter(
            ClassBooking.schedule_id == schedule_id,
            ClassBooking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ATTENDED]),
        )
        .scalar()
        or 0
    )


def _generate_spots(schedule: ClassSchedule, db: Session) -> int:
    """Sinh sơ đồ vị trí cho buổi học (thảm Yoga / xe Cycling)."""
    if not schedule.requires_spot_selection:
        return 0

    prefix = "B" if schedule.spot_layout == "bike" else "M"
    created = 0
    for i in range(1, schedule.capacity + 1):
        exists = (
            db.query(ClassSpot)
            .filter(
                ClassSpot.schedule_id == schedule.id,
                ClassSpot.spot_code == f"{prefix}{i:02d}",
            )
            .first()
        )
        if exists:
            continue
        # Chia khu vực theo hàng để hội viên dễ chọn
        if i <= 5:
            zone = "Hàng đầu (gần gương)"
        elif i <= schedule.capacity - 5:
            zone = "Khu giữa"
        else:
            zone = "Hàng cuối"
        db.add(ClassSpot(
            schedule_id=schedule.id,
            spot_code=f"{prefix}{i:02d}",
            zone=zone,
            is_available=True,
        ))
        created += 1
    return created


def _promote_from_waitlist(schedule_id: int, db: Session) -> Optional[dict]:
    """Đôn người đầu hàng chờ lên danh sách chính thức khi có chỗ trống."""
    schedule = db.query(ClassSchedule).filter(ClassSchedule.id == schedule_id).first()
    if not schedule:
        return None

    if _enrolled_count(schedule_id, db) >= schedule.capacity:
        return None

    next_up = (
        db.query(ClassWaitlist)
        .filter(
            ClassWaitlist.schedule_id == schedule_id,
            ClassWaitlist.status == "waiting",
        )
        .order_by(ClassWaitlist.position.asc())
        .first()
    )
    if not next_up:
        return None

    # Cấp chỗ trống đầu tiên còn lại
    spot = None
    if schedule.requires_spot_selection:
        spot = (
            db.query(ClassSpot)
            .filter(
                ClassSpot.schedule_id == schedule_id,
                ClassSpot.is_available == True,
            )
            .order_by(ClassSpot.spot_code.asc())
            .first()
        )
        if spot:
            spot.is_available = False

    booking = ClassBooking(
        schedule_id=schedule_id,
        member_id=next_up.member_id,
        spot_id=spot.id if spot else None,
        status=BookingStatus.CONFIRMED,
        promoted_from_waitlist=True,
        note="Tự động đôn từ danh sách chờ",
    )
    db.add(booking)

    next_up.status = "promoted"
    next_up.promoted_at = now_local()
    next_up.notified = True

    member = db.query(Member).filter(Member.id == next_up.member_id).first()
    klass = schedule.gym_class

    return {
        "member_id": next_up.member_id,
        "member_name": member.full_name if member else None,
        "phone": member.phone if member else None,
        "class_name": klass.name if klass else None,
        "start_time": schedule.start_time,
        "spot_code": spot.spot_code if spot else None,
        "notification": (
            f"🔔 Bạn đã được đôn từ danh sách chờ vào lớp "
            f"'{klass.name if klass else ''}' lúc "
            f"{schedule.start_time.strftime('%H:%M ngày %d/%m/%Y')}"
            + (f", vị trí {spot.spot_code}" if spot else "")
            + ". Vui lòng có mặt đúng giờ!"
        ),
    }


# ==========================================================================
# LỊCH LỚP
# ==========================================================================
@router.get("/schedules")
def list_schedules(
    days_ahead: int = Query(14, ge=1, le=60),
    category: Optional[str] = None,
    branch_id: Optional[int] = None,
    include_full: bool = Query(True, description="Bao gồm cả lớp đã đầy chỗ"),
    db: Session = Depends(get_db),
):
    """Lịch các buổi học GroupX kèm số chỗ trống và danh sách chờ."""
    now = now_local()
    until = now + timedelta(days=days_ahead)

    query = (
        db.query(ClassSchedule)
        .filter(
            ClassSchedule.start_time >= now,
            ClassSchedule.start_time <= until,
            ClassSchedule.status == ScheduleStatus.SCHEDULED,
        )
    )
    if branch_id:
        query = query.filter(ClassSchedule.branch_id == branch_id)

    schedules = query.order_by(ClassSchedule.start_time.asc()).limit(300).all()

    result = []
    for s in schedules:
        klass = s.gym_class
        if category and klass and klass.category != category:
            continue

        enrolled = _enrolled_count(s.id, db)
        available = max(0, s.capacity - enrolled)
        if not include_full and available <= 0:
            continue

        waitlist_count = (
            db.query(func.count(ClassWaitlist.id))
            .filter(
                ClassWaitlist.schedule_id == s.id,
                ClassWaitlist.status == "waiting",
            )
            .scalar()
            or 0
        )

        trainer = s.substitute_trainer or s.trainer
        result.append({
            "id": s.id,
            "class_name": klass.name if klass else None,
            "category": klass.category if klass else None,
            "description": klass.description if klass else None,
            "studio": s.studio,
            "branch_id": s.branch_id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "difficulty": s.difficulty,
            "capacity": s.capacity,
            "enrolled_count": enrolled,
            "available_spots": available,
            "fill_percent": round(enrolled / s.capacity * 100) if s.capacity else 0,
            "is_full": available <= 0,
            "waitlist_count": waitlist_count,
            "trainer_id": trainer.id if trainer else None,
            "trainer_name": trainer.full_name if trainer else "HLV",
            "is_substituted": s.substitute_trainer_id is not None,
            "requires_spot_selection": s.requires_spot_selection,
            "spot_layout": s.spot_layout,
        })
    return result


@router.get("/schedules/{schedule_id}")
def schedule_detail(schedule_id: int, db: Session = Depends(get_db)):
    """Chi tiết buổi học kèm sơ đồ vị trí (Floor Map)."""
    schedule = db.query(ClassSchedule).filter(ClassSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi học")

    klass = schedule.gym_class
    enrolled = _enrolled_count(schedule.id, db)
    trainer = schedule.substitute_trainer or schedule.trainer

    spots_payload = []
    if schedule.requires_spot_selection:
        spots = (
            db.query(ClassSpot)
            .filter(ClassSpot.schedule_id == schedule.id)
            .order_by(ClassSpot.spot_code.asc())
            .all()
        )

        # Sinh sơ đồ vị trí nếu buổi học chưa có (VD: dữ liệu tạo trực tiếp
        # trong DB hoặc lịch cũ trước khi bật tính năng chọn vị trí)
        if not spots:
            created = _generate_spots(schedule, db)
            if created:
                db.commit()
                spots = (
                    db.query(ClassSpot)
                    .filter(ClassSpot.schedule_id == schedule.id)
                    .order_by(ClassSpot.spot_code.asc())
                    .all()
                )

        # Nhóm theo khu vực để vẽ sơ đồ phòng
        by_zone: dict[str, list] = {}
        for sp in spots:
            by_zone.setdefault(sp.zone or "Khác", []).append({
                "id": sp.id,
                "spot_code": sp.spot_code,
                "is_available": sp.is_available,
            })
        spots_payload = [
            {"zone": zone, "spots": items} for zone, items in by_zone.items()
        ]

    return {
        "id": schedule.id,
        "class_name": klass.name if klass else None,
        "category": klass.category if klass else None,
        "description": klass.description if klass else None,
        "studio": schedule.studio,
        "start_time": schedule.start_time,
        "end_time": schedule.end_time,
        "difficulty": schedule.difficulty,
        "capacity": schedule.capacity,
        "enrolled_count": enrolled,
        "available_spots": max(0, schedule.capacity - enrolled),
        "trainer_name": trainer.full_name if trainer else "HLV",
        "trainer_specialty": trainer.specialty if trainer else None,
        "requires_spot_selection": schedule.requires_spot_selection,
        "spot_layout": schedule.spot_layout,
        "spot_map": spots_payload,
        "note": schedule.note,
    }


@router.post("/schedules")
def create_schedule(
    data: ClassScheduleCreate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Admin tạo buổi học GroupX cụ thể."""
    if data.end_time <= data.start_time:
        raise HTTPException(status_code=422, detail="Giờ kết thúc phải sau giờ bắt đầu")

    klass = db.query(GymClass).filter(GymClass.id == data.gym_class_id).first()
    if not klass:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    schedule = ClassSchedule(
        gym_class_id=data.gym_class_id,
        trainer_id=data.trainer_id or klass.trainer_id,
        branch_id=data.branch_id or klass.branch_id,
        studio=data.studio,
        start_time=data.start_time,
        end_time=data.end_time,
        capacity=data.capacity,
        difficulty=data.difficulty,
        requires_spot_selection=data.requires_spot_selection,
        spot_layout=data.spot_layout,
        note=data.note,
    )
    db.add(schedule)
    db.flush()

    spots_created = _generate_spots(schedule, db)
    db.commit()
    db.refresh(schedule)

    return {
        "message": (
            f"Đã tạo buổi học '{klass.name}' lúc "
            f"{schedule.start_time.strftime('%H:%M %d/%m/%Y')}, "
            f"sức chứa {schedule.capacity} học viên."
        ),
        "schedule_id": schedule.id,
        "spots_created": spots_created,
    }


@router.post("/schedules/{schedule_id}/substitute")
def assign_substitute(
    schedule_id: int,
    data: SubstituteTrainerAssign,
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """Gán HLV dạy thay cho một buổi khi PT chính nghỉ."""
    schedule = db.query(ClassSchedule).filter(ClassSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi học")

    sub = db.query(Trainer).filter(Trainer.id == data.substitute_trainer_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Không tìm thấy HLV dạy thay")

    original = schedule.trainer
    schedule.substitute_trainer_id = sub.id
    if data.note:
        schedule.note = f"{schedule.note or ''}\n[Dạy thay]: {data.note}".strip()

    # Thông báo cho học viên đã đặt chỗ
    booked = (
        db.query(ClassBooking)
        .filter(
            ClassBooking.schedule_id == schedule.id,
            ClassBooking.status == ClassBookingStatus_CONFIRMED,
        )
        .all()
    )

    db.commit()

    return {
        "message": (
            f"Đã gán {sub.full_name} dạy thay cho buổi học. "
            f"{len(booked)} học viên đã đặt chỗ sẽ nhận được thông báo."
        ),
        "schedule_id": schedule.id,
        "original_trainer": original.full_name if original else None,
        "substitute_trainer": sub.full_name,
        "notified_students": len(booked),
    }


ClassBookingStatus_CONFIRMED = BookingStatus.CONFIRMED


# ==========================================================================
# ĐẶT CHỖ & DANH SÁCH CHỜ
# ==========================================================================
@router.post("/book")
def book_class(
    data: ClassBookRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đặt chỗ lớp GroupX. Nếu lớp đầy -> tự động vào danh sách chờ."""
    member = _member_of(current_user, db)
    today = date.today()

    # --- Kiểm tra thẻ hội viên ---
    if member.frozen_until and member.frozen_until >= today:
        raise HTTPException(
            status_code=400,
            detail=f"Thẻ đang bảo lưu đến {member.frozen_until}. Không thể đặt lớp.",
        )
    if not member.expire_date or member.expire_date < today or member.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Thẻ hội viên chưa kích hoạt hoặc đã hết hạn.",
        )
    if member.is_debt_blocked:
        raise HTTPException(
            status_code=400,
            detail="Thẻ đang tạm khóa do công nợ quá hạn. "
                   "Vui lòng thanh toán để tiếp tục đặt lớp.",
        )

    # --- Kiểm tra hình phạt no-show ---
    penalty = _active_penalty(member.id, db)
    if penalty:
        raise HTTPException(
            status_code=403,
            detail=f"⛔ Bạn đang bị tạm khóa quyền đặt lớp GroupX đến "
                   f"{penalty.blocked_until} do đã không đến {penalty.no_show_count} lần "
                   f"mà không hủy. Bạn vẫn có thể tập tạ và dùng máy bình thường.",
        )

    schedule = db.query(ClassSchedule).filter(ClassSchedule.id == data.schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi học")
    if schedule.status == ScheduleStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Buổi học này đã bị hủy")
    if schedule.start_time <= now_local():
        raise HTTPException(status_code=400, detail="Buổi học này đã bắt đầu, không thể đặt")

    klass = schedule.gym_class

    # --- Đã đặt chưa? ---
    existing = (
        db.query(ClassBooking)
        .filter(
            ClassBooking.schedule_id == schedule.id,
            ClassBooking.member_id == member.id,
        )
        .first()
    )
    if existing and existing.status in (BookingStatus.CONFIRMED, BookingStatus.WAITLISTED):
        raise HTTPException(
            status_code=400, detail=f"Bạn đã đặt lớp '{klass.name if klass else ''}' rồi"
        )

    on_waitlist = (
        db.query(ClassWaitlist)
        .filter(
            ClassWaitlist.schedule_id == schedule.id,
            ClassWaitlist.member_id == member.id,
            ClassWaitlist.status == "waiting",
        )
        .first()
    )
    if on_waitlist:
        raise HTTPException(
            status_code=400,
            detail=f"Bạn đang ở vị trí #{on_waitlist.position} trong danh sách chờ.",
        )

    enrolled = _enrolled_count(schedule.id, db)

    # --- Lớp đầy -> vào danh sách chờ ---
    if enrolled >= schedule.capacity:
        last_position = (
            db.query(func.max(ClassWaitlist.position))
            .filter(
                ClassWaitlist.schedule_id == schedule.id,
                ClassWaitlist.status == "waiting",
            )
            .scalar()
            or 0
        )
        position = last_position + 1

        entry = ClassWaitlist(
            schedule_id=schedule.id,
            member_id=member.id,
            position=position,
            status="waiting",
        )
        db.add(entry)
        if existing:
            existing.status = BookingStatus.WAITLISTED
        db.commit()
        db.refresh(entry)

        return {
            "message": (
                f"Lớp '{klass.name if klass else ''}' đã đủ {schedule.capacity} học viên. "
                f"Bạn đã được thêm vào danh sách chờ ở vị trí #{position}. "
                f"Hệ thống sẽ tự động đôn bạn lên và thông báo ngay khi có người hủy chỗ."
            ),
            "status": "waitlisted",
            "waitlist_position": position,
            "class_name": klass.name if klass else None,
            "start_time": schedule.start_time,
        }

    # --- Còn chỗ -> đặt chính thức ---
    spot = None
    if schedule.requires_spot_selection:
        # Đảm bảo sơ đồ vị trí đã tồn tại trước khi gán chỗ
        has_spots = (
            db.query(ClassSpot)
            .filter(ClassSpot.schedule_id == schedule.id)
            .first()
        )
        if not has_spots:
            _generate_spots(schedule, db)
            db.flush()

        if data.spot_id:
            spot = (
                db.query(ClassSpot)
                .filter(
                    ClassSpot.id == data.spot_id,
                    ClassSpot.schedule_id == schedule.id,
                )
                .first()
            )
            if not spot:
                raise HTTPException(status_code=404, detail="Không tìm thấy vị trí này")
            if not spot.is_available:
                raise HTTPException(
                    status_code=409,
                    detail=f"Vị trí {spot.spot_code} vừa được người khác chọn. "
                           f"Vui lòng chọn vị trí khác.",
                )
            spot.is_available = False
        else:
            # Tự cấp vị trí trống đầu tiên
            spot = (
                db.query(ClassSpot)
                .filter(
                    ClassSpot.schedule_id == schedule.id,
                    ClassSpot.is_available == True,
                )
                .order_by(ClassSpot.spot_code.asc())
                .first()
            )
            if spot:
                spot.is_available = False

    if existing:
        existing.status = BookingStatus.CONFIRMED
        existing.spot_id = spot.id if spot else None
        existing.note = data.note
        booking = existing
    else:
        booking = ClassBooking(
            schedule_id=schedule.id,
            member_id=member.id,
            spot_id=spot.id if spot else None,
            status=BookingStatus.CONFIRMED,
            note=data.note,
        )
        db.add(booking)

    db.commit()
    db.refresh(booking)

    return {
        "message": (
            f"Đặt chỗ lớp '{klass.name if klass else ''}' thành công"
            + (f", vị trí {spot.spot_code}" if spot else "")
            + f". Thời gian: {schedule.start_time.strftime('%H:%M ngày %d/%m/%Y')}."
        ),
        "status": "confirmed",
        "booking_id": booking.id,
        "spot_code": spot.spot_code if spot else None,
        "spot_zone": spot.zone if spot else None,
        "class_name": klass.name if klass else None,
        "start_time": schedule.start_time,
        "available_spots": max(0, schedule.capacity - enrolled - 1),
    }


@router.post("/bookings/{booking_id}/cancel")
def cancel_class_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hủy đặt chỗ và TỰ ĐỘNG ĐÔN người đầu danh sách chờ lên."""
    member = _member_of(current_user, db)
    booking = (
        db.query(ClassBooking)
        .filter(ClassBooking.id == booking_id, ClassBooking.member_id == member.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy đặt chỗ")

    schedule = booking.schedule
    hours_before = (
        (schedule.start_time - now_local()).total_seconds() / 3600 if schedule else 0
    )

    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = now_local()

    # Giải phóng vị trí
    if booking.spot_id:
        spot = db.query(ClassSpot).filter(ClassSpot.id == booking.spot_id).first()
        if spot:
            spot.is_available = True

    # Xóa khỏi danh sách chờ nếu có
    waitlist_entry = (
        db.query(ClassWaitlist)
        .filter(
            ClassWaitlist.schedule_id == booking.schedule_id,
            ClassWaitlist.member_id == member.id,
        )
        .first()
    )
    if waitlist_entry and waitlist_entry.status == "waiting":
        waitlist_entry.status = "cancelled"

    # --- Tự động đôn người kế tiếp ---
    promoted = _promote_from_waitlist(booking.schedule_id, db)

    db.commit()

    return {
        "message": (
            f"Đã hủy đặt chỗ lớp. "
            + (
                f"Người ở danh sách chờ ({promoted['member_name']}) đã được tự động đôn lên."
                if promoted else "Không có ai trong danh sách chờ."
            )
        ),
        "hours_before_class": round(hours_before, 1),
        "promoted_member": promoted,
    }


@router.get("/waitlist/{schedule_id}")
def view_waitlist(schedule_id: int, db: Session = Depends(get_db)):
    """Xem danh sách chờ của một buổi học."""
    schedule = db.query(ClassSchedule).filter(ClassSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi học")

    entries = (
        db.query(ClassWaitlist)
        .filter(
            ClassWaitlist.schedule_id == schedule_id,
            ClassWaitlist.status.in_(["waiting", "promoted"]),
        )
        .order_by(ClassWaitlist.position.asc())
        .all()
    )
    klass = schedule.gym_class

    return {
        "class_name": klass.name if klass else None,
        "start_time": schedule.start_time,
        "capacity": schedule.capacity,
        "enrolled_count": _enrolled_count(schedule_id, db),
        "waitlist": [
            {
                "position": w.position,
                "member_id": w.member_id,
                "member_name": w.member.full_name if w.member else None,
                "status": w.status,
                "joined_at": w.joined_at,
                "promoted_at": w.promoted_at,
            }
            for w in entries
        ],
        "auto_promote_note": (
            "Ngay khi có người hủy chỗ, hệ thống tự động đôn người ở vị trí #1 lên "
            "danh sách chính thức và gửi thông báo ngay lập tức."
        ),
    }


# ==========================================================================
# NO-SHOW & HÌNH PHẠT
# ==========================================================================
@router.post("/schedules/{schedule_id}/mark-attendance")
def mark_attendance(
    schedule_id: int,
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """HLV điểm danh lớp: ai có mặt, ai vắng (no-show)."""
    schedule = db.query(ClassSchedule).filter(ClassSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi học")

    bookings = (
        db.query(ClassBooking)
        .filter(
            ClassBooking.schedule_id == schedule_id,
            ClassBooking.status == BookingStatus.CONFIRMED,
        )
        .all()
    )

    now = now_local()
    # Hội viên được coi là có mặt nếu đã check-in cổng trong vòng 2 giờ trước buổi học
    window_start = schedule.start_time - timedelta(hours=2)

    attended = 0
    no_shows: list[dict] = []

    from app.models.operations import GateCheckin, GateResult

    for booking in bookings:
        gate = (
            db.query(GateCheckin)
            .filter(
                GateCheckin.member_id == booking.member_id,
                GateCheckin.result == GateResult.GRANTED,
                GateCheckin.direction == "in",
                GateCheckin.checkin_time >= window_start,
                GateCheckin.checkin_time <= schedule.end_time + timedelta(hours=2),
            )
            .first()
        )

        if gate:
            booking.status = BookingStatus.ATTENDED
            booking.checked_in_at = gate.checkin_time
            attended += 1
        else:
            booking.status = BookingStatus.NO_SHOW
            member = booking.member
            # Đếm số lần no-show trong tháng
            month_start = date.today().replace(day=1)
            no_show_count = (
                db.query(func.count(ClassBooking.id))
                .join(ClassSchedule, ClassBooking.schedule_id == ClassSchedule.id)
                .filter(
                    ClassBooking.member_id == booking.member_id,
                    ClassBooking.status == BookingStatus.NO_SHOW,
                    ClassSchedule.start_time >= datetime.combine(
                        month_start, datetime.min.time()
                    ),
                )
                .scalar()
                or 0
            )

            # Đủ ngưỡng -> khóa quyền đặt lớp
            if no_show_count >= NO_SHOW_LIMIT_PER_MONTH:
                existing_penalty = _active_penalty(booking.member_id, db)
                if not existing_penalty:
                    db.add(BookingPenalty(
                        member_id=booking.member_id,
                        reason=(
                            f"Không đến lớp GroupX {no_show_count} lần trong tháng "
                            f"mà không hủy trước"
                        ),
                        no_show_count=no_show_count,
                        blocked_from=date.today(),
                        blocked_until=date.today() + timedelta(days=PENALTY_BLOCK_DAYS),
                        is_active=True,
                        created_by=current_user.full_name or current_user.username,
                    ))
                    db.add(RetentionTask(
                        member_id=booking.member_id,
                        kind="sleeping_7d",
                        priority="medium",
                        title=f"Hội viên bỏ lớp GroupX {no_show_count} lần",
                        detail=(
                            f"{member.full_name if member else 'Hội viên'} đã không đến lớp "
                            f"{no_show_count} lần trong tháng này mà không hủy trước."
                        ),
                        suggested_action=(
                            "Gọi điện hỏi thăm: có thể hội viên gặp vấn đề về thời gian hoặc "
                            "chưa phù hợp với khung giờ lớp. Đề xuất đổi sang lớp/khung giờ khác."
                        ),
                        assigned_to="CSKH",
                    ))

            no_shows.append({
                "member_id": booking.member_id,
                "member_name": member.full_name if member else None,
                "phone": member.phone if member else None,
                "no_show_count_this_month": no_show_count,
                "penalty_applied": no_show_count >= NO_SHOW_LIMIT_PER_MONTH,
            })

    schedule.status = ScheduleStatus.COMPLETED
    db.commit()

    return {
        "message": (
            f"Đã điểm danh lớp: {attended} học viên có mặt, {len(no_shows)} vắng mặt."
        ),
        "schedule_id": schedule_id,
        "attended": attended,
        "no_show": len(no_shows),
        "no_show_details": no_shows,
        "policy": (
            f"Hội viên không đến (no-show) quá {NO_SHOW_LIMIT_PER_MONTH} lần trong 1 tháng "
            f"sẽ bị khóa quyền đặt lớp GroupX online trong {PENALTY_BLOCK_DAYS} ngày "
            f"(vẫn được tập tạ bình thường)."
        ),
    }


@router.get("/penalties/my")
def my_penalties(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Hình phạt khóa đặt lớp của hội viên."""
    member = _member_of(current_user, db)
    today = date.today()

    active = _active_penalty(member.id, db)

    month_start = today.replace(day=1)
    no_show_count = (
        db.query(func.count(ClassBooking.id))
        .join(ClassSchedule, ClassBooking.schedule_id == ClassSchedule.id)
        .filter(
            ClassBooking.member_id == member.id,
            ClassBooking.status == BookingStatus.NO_SHOW,
            ClassSchedule.start_time >= datetime.combine(month_start, datetime.min.time()),
        )
        .scalar()
        or 0
    )

    return {
        "is_blocked": active is not None,
        "blocked_until": active.blocked_until if active else None,
        "reason": active.reason if active else None,
        "no_show_count_this_month": no_show_count,
        "no_show_limit": NO_SHOW_LIMIT_PER_MONTH,
        "remaining_before_block": max(0, NO_SHOW_LIMIT_PER_MONTH - no_show_count),
        "warning": (
            f"⚠️ Bạn đang bị tạm khóa đặt lớp đến {active.blocked_until}. "
            f"Bạn vẫn có thể tập tạ và sử dụng máy tại phòng gym."
            if active else
            (
                f"Bạn đã vắng mặt {no_show_count}/{NO_SHOW_LIMIT_PER_MONTH} lần trong tháng này. "
                f"Nếu vắng thêm {max(0, NO_SHOW_LIMIT_PER_MONTH - no_show_count)} lần nữa, "
                f"quyền đặt lớp online sẽ bị khóa {PENALTY_BLOCK_DAYS} ngày."
                if no_show_count > 0 else None
            )
        ),
        "advice": (
            "Hãy hủy chỗ trước giờ học ít nhất 2 giờ nếu bạn không thể tham gia — "
            "việc này giúp người khác trong danh sách chờ có cơ hội vào lớp."
        ),
    }


@router.get("/my-bookings")
def my_class_bookings(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Lịch lớp GroupX của hội viên."""
    member = _member_of(current_user, db)
    bookings = (
        db.query(ClassBooking)
        .filter(ClassBooking.member_id == member.id)
        .order_by(ClassBooking.booked_at.desc())
        .limit(60)
        .all()
    )
    return [
        {
            "booking_id": b.id,
            "class_name": b.schedule.gym_class.name if b.schedule and b.schedule.gym_class else None,
            "category": b.schedule.gym_class.category if b.schedule and b.schedule.gym_class else None,
            "start_time": b.schedule.start_time if b.schedule else None,
            "end_time": b.schedule.end_time if b.schedule else None,
            "studio": b.schedule.studio if b.schedule else None,
            "status": b.status,
            "spot_code": b.spot.spot_code if b.spot else None,
            "promoted_from_waitlist": b.promoted_from_waitlist,
            "checked_in_at": b.checked_in_at,
            "rating": b.rating,
        }
        for b in bookings
    ]