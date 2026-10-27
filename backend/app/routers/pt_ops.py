"""Router NGHIỆP VỤ PT — gói buổi tập, ca làm việc, chống gian lận trừ buổi,
đổi PT/dạy thay và tính lương hoa hồng.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.engagement import PointKind
from app.models.interaction import now_local
from app.models.operations import GateCheckin, GateResult
from app.models.pt import PTBooking, TrainerSlot
from app.models.trainer_ops import (
    PackageStatus, PTBurnConfirmation, PTPackage, PTPackagePurchase,
    SessionOutcome, TrainerChangeRequest, TrainerPayroll, TrainerShift,
)
from app.models.user import Member, Role, Trainer, User
from app.schemas.erp import (
    BurnConfirmRequest, BurnSessionRequest, PayrollGenerate,
    PTPackageCreate, PTPackagePurchaseCreate, TrainerChangeCreate,
    TrainerShiftCreate,
)
from app.security import (
    get_current_user, require_operations, require_trainer_or_admin,
)

router = APIRouter(prefix="/pt-ops", tags=["PT Operations & Chống gian lận"])


#: Hủy lịch trước bao nhiêu giờ thì được hoàn buổi
EARLY_CANCEL_HOURS = 6
#: Sau bao nhiêu phút không đến thì tính là no-show
NO_SHOW_MINUTES = 30
#: Thưởng đánh giá 5 sao
FIVE_STAR_BONUS = 300000


def _member_of(user: User, db: Session) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hội viên")
    return member


def _trainer_of(user: User, db: Session) -> Trainer:
    trainer = db.query(Trainer).filter(Trainer.user_id == user.id).first()
    if not trainer:
        raise HTTPException(
            status_code=404,
            detail="Tài khoản của bạn chưa được gắn với hồ sơ Huấn luyện viên.",
        )
    return trainer


def _active_purchase(member_id: int, db: Session) -> Optional[PTPackagePurchase]:
    """Gói PT đang hiệu lực và còn buổi của hội viên."""
    return (
        db.query(PTPackagePurchase)
        .filter(
            PTPackagePurchase.member_id == member_id,
            PTPackagePurchase.status == PackageStatus.ACTIVE,
            PTPackagePurchase.sessions_remaining > 0,
            PTPackagePurchase.expiry_date >= date.today(),
        )
        .order_by(PTPackagePurchase.expiry_date.asc())
        .first()
    )


def _award_points(member_id: int, points: int, kind: str, note: str, db: Session) -> int:
    """Cộng điểm thưởng và trả về số dư mới."""
    from app.models.engagement import LoyaltyPoint

    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return 0
    new_balance = (member.loyalty_points or 0) + points
    member.loyalty_points = new_balance
    member.total_points_earned = (member.total_points_earned or 0) + max(0, points)
    db.add(LoyaltyPoint(
        member_id=member_id, points=points, balance_after=new_balance,
        kind=kind, note=note,
    ))
    return new_balance


# ==========================================================================
# GÓI TẬP PT (SESSION-BASED)
# ==========================================================================
@router.get("/packages")
def list_pt_packages(db: Session = Depends(get_db)):
    """Danh mục gói tập PT (tính theo số buổi)."""
    pkgs = (
        db.query(PTPackage)
        .filter(PTPackage.is_active == True)
        .order_by(PTPackage.sessions.asc())
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "sessions": p.sessions,
            "price": p.price,
            "price_per_session": p.unit_price,
            "validity_days": p.validity_days,
            "tier": p.tier,
            "includes_inbody": p.includes_inbody,
            "includes_nutrition": p.includes_nutrition,
            "description": p.description,
        }
        for p in pkgs
    ]


@router.post("/packages")
def create_pt_package(
    data: PTPackageCreate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Tạo gói tập PT mới (Admin/Lễ tân)."""
    pkg = PTPackage(
        name=data.name,
        sessions=data.sessions,
        price=data.price,
        validity_days=data.validity_days,
        price_per_session=round(data.price / data.sessions, 0) if data.sessions else 0,
        tier=data.tier,
        includes_inbody=data.includes_inbody,
        includes_nutrition=data.includes_nutrition,
        description=data.description,
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return {
        "message": f"Đã tạo gói PT '{pkg.name}' ({pkg.sessions} buổi)",
        "package_id": pkg.id,
        "price_per_session": pkg.unit_price,
    }


@router.post("/packages/purchase")
def purchase_pt_package(
    data: PTPackagePurchaseCreate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Hội viên mua gói PT — sinh quyền sử dụng buổi tập."""
    member = db.query(Member).filter(Member.id == data.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")

    pkg = db.query(PTPackage).filter(
        PTPackage.id == data.package_id, PTPackage.is_active == True
    ).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Gói PT không tồn tại")

    if data.trainer_id:
        trainer = db.query(Trainer).filter(Trainer.id == data.trainer_id).first()
        if not trainer:
            raise HTTPException(status_code=404, detail="Không tìm thấy Huấn luyện viên")
        if trainer.current_trainees >= trainer.max_trainees:
            raise HTTPException(
                status_code=400,
                detail=f"HLV {trainer.full_name} đã đạt giới hạn {trainer.max_trainees} "
                       f"học viên. Vui lòng chọn HLV khác.",
            )

    today = date.today()
    purchase = PTPackagePurchase(
        member_id=member.id,
        package_id=pkg.id,
        trainer_id=data.trainer_id,
        sessions_total=pkg.sessions,
        sessions_used=0,
        sessions_remaining=pkg.sessions,
        price=pkg.price,
        paid_amount=pkg.price,
        start_date=today,
        expiry_date=today + timedelta(days=pkg.validity_days),
        status=PackageStatus.ACTIVE,
        sold_by=data.sold_by or current_user.full_name or current_user.username,
    )
    db.add(purchase)

    # Gán HLV phụ trách
    if data.trainer_id:
        member.trainer_id = data.trainer_id
        trainer = db.query(Trainer).filter(Trainer.id == data.trainer_id).first()
        if trainer:
            trainer.current_trainees = (trainer.current_trainees or 0) + 1

    db.commit()
    db.refresh(purchase)

    return {
        "message": (
            f"Đã kích hoạt gói '{pkg.name}' với {pkg.sessions} buổi cho {member.full_name}. "
            f"Hạn sử dụng đến {purchase.expiry_date}."
        ),
        "purchase_id": purchase.id,
        "sessions_total": purchase.sessions_total,
        "sessions_remaining": purchase.sessions_remaining,
        "expiry_date": purchase.expiry_date,
        "price_per_session": pkg.unit_price,
    }


@router.get("/packages/my")
def my_pt_packages(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Gói PT và số buổi còn lại của hội viên."""
    member = _member_of(current_user, db)
    purchases = (
        db.query(PTPackagePurchase)
        .filter(PTPackagePurchase.member_id == member.id)
        .order_by(PTPackagePurchase.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "package_name": p.package.name if p.package else None,
            "trainer_name": p.trainer.full_name if p.trainer else None,
            "sessions_total": p.sessions_total,
            "sessions_used": p.sessions_used,
            "sessions_remaining": p.sessions_remaining,
            "usage_percent": round(p.sessions_used / p.sessions_total * 100)
            if p.sessions_total else 0,
            "start_date": p.start_date,
            "expiry_date": p.expiry_date,
            "days_remaining": p.days_remaining,
            "status": p.status,
            "warning": (
                f"⚠️ Gói còn {p.sessions_remaining} buổi nhưng chỉ còn "
                f"{p.days_remaining} ngày. Hãy đặt lịch tập sớm!"
                if p.status == PackageStatus.ACTIVE and p.days_remaining <= 14
                and p.sessions_remaining > 0 else None
            ),
        }
        for p in purchases
    ]


# ==========================================================================
# CA LÀM VIỆC CỦA PT
# ==========================================================================
@router.post("/shifts")
def create_shift(
    data: TrainerShiftCreate,
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """PT đăng ký ca làm việc trong tuần."""
    if data.end_hour <= data.start_hour:
        raise HTTPException(status_code=422, detail="Giờ kết thúc phải sau giờ bắt đầu")

    trainer = _trainer_of(current_user, db) if Role.normalize(current_user.role) == Role.TRAINER \
        else db.query(Trainer).filter(Trainer.id == data.trainer_id).first()
    if not trainer:
        raise HTTPException(status_code=404, detail="Không tìm thấy Huấn luyện viên")

    existing = (
        db.query(TrainerShift)
        .filter(
            TrainerShift.trainer_id == trainer.id,
            TrainerShift.weekday == data.weekday,
            TrainerShift.start_hour == data.start_hour,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Ca làm việc này đã tồn tại cho HLV"
        )

    shift = TrainerShift(
        trainer_id=trainer.id,
        branch_id=data.branch_id or trainer.branch_id,
        weekday=data.weekday,
        start_hour=data.start_hour,
        end_hour=data.end_hour,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)

    weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
    return {
        "message": (
            f"Đã đăng ký ca {weekday_names[data.weekday]} "
            f"{data.start_hour:02d}:00 - {data.end_hour:02d}:00 cho {trainer.full_name}"
        ),
        "shift_id": shift.id,
    }


@router.get("/shifts")
def list_shifts(
    trainer_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """Danh sách ca làm việc."""
    query = db.query(TrainerShift).filter(TrainerShift.is_active == True)
    if trainer_id:
        query = query.filter(TrainerShift.trainer_id == trainer_id)
    shifts = query.order_by(TrainerShift.trainer_id, TrainerShift.weekday).all()

    weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
    return [
        {
            "id": s.id,
            "trainer_id": s.trainer_id,
            "trainer_name": s.trainer.full_name if s.trainer else None,
            "weekday": s.weekday,
            "weekday_name": weekday_names[s.weekday] if 0 <= s.weekday <= 6 else "?",
            "start_hour": s.start_hour,
            "end_hour": s.end_hour,
            "time_range": f"{s.start_hour:02d}:00 - {s.end_hour:02d}:00",
            "branch_id": s.branch_id,
        }
        for s in shifts
    ]


@router.post("/shifts/generate-slots")
def generate_slots_from_shifts(
    trainer_id: int,
    days_ahead: int = Query(14, ge=1, le=60),
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """Sinh khung giờ trống từ ca làm việc của PT (tự động mở lịch 60 phút)."""
    trainer = db.query(Trainer).filter(Trainer.id == trainer_id).first()
    if not trainer:
        raise HTTPException(status_code=404, detail="Không tìm thấy Huấn luyện viên")

    shifts = (
        db.query(TrainerShift)
        .filter(TrainerShift.trainer_id == trainer_id, TrainerShift.is_active == True)
        .all()
    )
    if not shifts:
        raise HTTPException(
            status_code=400,
            detail="HLV chưa đăng ký ca làm việc. Vui lòng đăng ký ca trước.",
        )

    # weekday 0 = Thứ 2 -> Python weekday(): 0 = Thứ 2
    today = date.today()
    created = 0
    skipped = 0

    for offset in range(days_ahead):
        the_date = today + timedelta(days=offset)
        py_weekday = the_date.weekday()

        for shift in shifts:
            if shift.weekday != py_weekday:
                continue

            for hour in range(shift.start_hour, shift.end_hour):
                start = datetime.combine(the_date, datetime.min.time()).replace(hour=hour)
                end = start + timedelta(hours=1)

                if start <= now_local():
                    skipped += 1
                    continue

                exists = (
                    db.query(TrainerSlot)
                    .filter(
                        TrainerSlot.trainer_id == trainer_id,
                        TrainerSlot.start_time == start,
                    )
                    .first()
                )
                if exists:
                    skipped += 1
                    continue

                db.add(TrainerSlot(
                    trainer_id=trainer_id,
                    branch_id=shift.branch_id or trainer.branch_id,
                    start_time=start,
                    end_time=end,
                    is_booked=False,
                    note="Buổi tập 1-1 — 60 phút",
                ))
                created += 1

    db.commit()
    return {
        "message": (
            f"Đã sinh {created} khung giờ trống cho {trainer.full_name} "
            f"trong {days_ahead} ngày tới ({skipped} khung giờ đã tồn tại hoặc đã qua)."
        ),
        "created": created,
        "skipped": skipped,
    }


# ==========================================================================
# HỦY LỊCH & CHÍNH SÁCH NO-SHOW
# ==========================================================================
@router.post("/bookings/{booking_id}/cancel")
def cancel_booking_with_policy(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hủy lịch PT với chính sách hoàn/trừ buổi theo thời điểm hủy.

    - Hủy trước >= 6 giờ  -> HOÀN buổi (early_cancel)
    - Hủy sát giờ < 6 giờ -> TRỪ buổi (late_cancel), bảo vệ thời gian của PT
    """
    member = _member_of(current_user, db)
    booking = (
        db.query(PTBooking)
        .filter(PTBooking.id == booking_id, PTBooking.member_id == member.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch đặt")
    if booking.status != "confirmed":
        raise HTTPException(
            status_code=400, detail=f"Lịch đã ở trạng thái '{booking.status}', không thể hủy"
        )

    slot = booking.slot
    now = now_local()
    hours_before = (slot.start_time - now).total_seconds() / 3600 if slot else 0

    purchase = _active_purchase(member.id, db)

    if hours_before >= EARLY_CANCEL_HOURS:
        # Hủy hợp lệ -> hoàn buổi (không trừ)
        outcome = SessionOutcome.EARLY_CANCEL
        deducted = False
        message = (
            f"Đã hủy lịch tập (hủy trước {hours_before:.1f} giờ). "
            f"Buổi tập được HOÀN lại vào tài khoản của bạn."
        )
    else:
        # Hủy muộn -> trừ buổi
        outcome = SessionOutcome.LATE_CANCEL
        deducted = False
        if purchase:
            purchase.sessions_used = (purchase.sessions_used or 0) + 1
            purchase.sessions_remaining = max(0, purchase.sessions_remaining - 1)
            if purchase.sessions_remaining == 0:
                purchase.status = PackageStatus.EXHAUSTED
            deducted = True

        message = (
            f"⚠️ Bạn hủy lịch chỉ trước giờ tập {hours_before:.1f} giờ "
            f"(quy định là trước {EARLY_CANCEL_HOURS} giờ). "
            + (
                f"Theo chính sách, buổi tập này được tính là ĐÃ SỬ DỤNG "
                f"(còn lại {purchase.sessions_remaining} buổi)."
                if deducted else
                "Tuy nhiên bạn chưa có gói PT đang hiệu lực nên không bị trừ buổi."
            )
        )

    booking.status = "cancelled"
    if slot:
        slot.is_booked = False

    # Ghi nhận vào bảng xác nhận kép để có audit trail
    confirmation = (
        db.query(PTBurnConfirmation)
        .filter(PTBurnConfirmation.booking_id == booking.id)
        .first()
    )
    if not confirmation:
        confirmation = PTBurnConfirmation(
            booking_id=booking.id,
            member_id=member.id,
            trainer_id=booking.trainer_id,
            purchase_id=purchase.id if purchase else None,
        )
        db.add(confirmation)
    confirmation.outcome = outcome
    confirmation.session_deducted = deducted
    confirmation.resolved_at = now

    db.commit()

    return {
        "message": message,
        "outcome": outcome,
        "hours_before_session": round(hours_before, 1),
        "session_deducted": deducted,
        "sessions_remaining": purchase.sessions_remaining if purchase else None,
    }


@router.post("/bookings/sweep-no-shows")
def sweep_no_shows(
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """Quét các buổi tập quá 30 phút mà hội viên không đến -> tính no-show, trừ buổi."""
    now = now_local()
    cutoff = now - timedelta(minutes=NO_SHOW_MINUTES)

    stale = (
        db.query(PTBooking)
        .join(TrainerSlot, PTBooking.slot_id == TrainerSlot.id)
        .filter(
            PTBooking.status == "confirmed",
            TrainerSlot.start_time <= cutoff,
            TrainerSlot.start_time >= now - timedelta(days=7),
        )
        .all()
    )

    processed = 0
    deducted_count = 0

    for booking in stale:
        purchase = _active_purchase(booking.member_id, db)

        confirmation = (
            db.query(PTBurnConfirmation)
            .filter(PTBurnConfirmation.booking_id == booking.id)
            .first()
        )
        if not confirmation:
            confirmation = PTBurnConfirmation(
                booking_id=booking.id,
                member_id=booking.member_id,
                trainer_id=booking.trainer_id,
                purchase_id=purchase.id if purchase else None,
            )
            db.add(confirmation)

        # Nếu hội viên đã xác nhận -> không phải no-show
        if confirmation.member_confirmed:
            continue

        deducted = False
        if purchase and purchase.sessions_remaining > 0:
            purchase.sessions_used = (purchase.sessions_used or 0) + 1
            purchase.sessions_remaining = max(0, purchase.sessions_remaining - 1)
            if purchase.sessions_remaining == 0:
                purchase.status = PackageStatus.EXHAUSTED
            deducted = True
            deducted_count += 1

        confirmation.outcome = SessionOutcome.NO_SHOW
        confirmation.session_deducted = deducted
        confirmation.resolved_at = now

        booking.status = "no_show"
        processed += 1

    db.commit()
    return {
        "message": (
            f"Đã xử lý {processed} buổi tập không đến. "
            f"{deducted_count} buổi bị trừ theo chính sách no-show."
        ),
        "processed": processed,
        "deducted": deducted_count,
        "policy": (
            f"Hội viên không đến sau {NO_SHOW_MINUTES} phút mà không hủy trước "
            f"{EARLY_CANCEL_HOURS} giờ sẽ bị trừ 1 buổi tập."
        ),
    }


# ==========================================================================
# XÁC NHẬN KÉP TRỪ BUỔI (CHỐNG GIAN LẬN)
# ==========================================================================
@router.post("/burn/mark")
def trainer_mark_complete(
    data: BurnSessionRequest,
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """BƯỚC 1: PT đánh dấu buổi tập đã dạy xong.

    LƯU Ý: bước này KHÔNG trừ buổi và KHÔNG ghi nhận hoa hồng.
    Buổi chỉ được tính khi hội viên xác nhận (bước 2) — đây là cơ chế chống
    gian lận bảo vệ quyền lợi hội viên.
    """
    trainer = _trainer_of(current_user, db)
    booking = (
        db.query(PTBooking)
        .filter(PTBooking.id == data.booking_id, PTBooking.trainer_id == trainer.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi tập của bạn")

    if booking.status == "completed":
        raise HTTPException(status_code=400, detail="Buổi tập này đã hoàn thành rồi")
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Buổi tập này đã bị hủy")

    confirmation = (
        db.query(PTBurnConfirmation)
        .filter(PTBurnConfirmation.booking_id == booking.id)
        .first()
    )
    if not confirmation:
        purchase = _active_purchase(booking.member_id, db)
        confirmation = PTBurnConfirmation(
            booking_id=booking.id,
            member_id=booking.member_id,
            trainer_id=trainer.id,
            purchase_id=purchase.id if purchase else None,
        )
        db.add(confirmation)

    # --- Kiểm tra điều kiện 1: hội viên có check-in tại cổng trong ngày ---
    today_start = datetime.combine(date.today(), datetime.min.time())
    gate = (
        db.query(GateCheckin)
        .filter(
            GateCheckin.member_id == booking.member_id,
            GateCheckin.result == GateResult.GRANTED,
            GateCheckin.direction == "in",
            GateCheckin.checkin_time >= today_start,
        )
        .order_by(GateCheckin.checkin_time.desc())
        .first()
    )
    confirmation.member_checked_in = gate is not None
    confirmation.gate_checkin_id = gate.id if gate else None
    confirmation.trainer_marked_at = now_local()
    confirmation.outcome = "pending"

    db.commit()

    member = db.query(Member).filter(Member.id == booking.member_id).first()

    return {
        "message": (
            f"Đã ghi nhận hoàn thành buổi tập với {member.full_name if member else 'hội viên'}. "
            f"Đang chờ hội viên xác nhận để trừ buổi."
        ),
        "booking_id": booking.id,
        "check_1_member_checked_in": confirmation.member_checked_in,
        "check_2_member_confirmed": confirmation.member_confirmed,
        "both_confirmed": False,
        "session_deducted": False,
        "note": (
            "Điều kiện 1/2 đã đạt (hội viên đã check-in tại cổng). "
            "Cần hội viên xác nhận cuối buổi để hoàn tất."
            if confirmation.member_checked_in else
            "⚠️ Hội viên CHƯA check-in tại cổng hôm nay. Theo quy định chống gian lận, "
            "buổi tập sẽ không được trừ cho tới khi có xác nhận của hội viên."
        ),
    }


@router.post("/burn/confirm")
def member_confirm_session(
    data: BurnConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """BƯỚC 2: Hội viên xác nhận cuối buổi (QR / OTP / nút app) kèm đánh giá sao.

    Chỉ khi BƯỚC 1 + BƯỚC 2 đều đạt thì buổi mới bị trừ và PT mới được ghi nhận
    hoa hồng. Đây là cơ chế Dual-Confirmation.
    """
    member = _member_of(current_user, db)
    booking = (
        db.query(PTBooking)
        .filter(PTBooking.id == data.booking_id, PTBooking.member_id == member.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi tập")

    confirmation = (
        db.query(PTBurnConfirmation)
        .filter(PTBurnConfirmation.booking_id == booking.id)
        .first()
    )
    if not confirmation:
        raise HTTPException(
            status_code=400,
            detail="HLV chưa đánh dấu hoàn thành buổi tập này. "
                   "Vui lòng yêu cầu HLV xác nhận trước.",
        )

    if confirmation.session_deducted:
        raise HTTPException(
            status_code=400, detail="Buổi tập này đã được xác nhận và trừ trước đó rồi"
        )

    # --- OTP: kiểm tra nếu xác nhận bằng OTP ---
    if data.method == "otp":
        if not data.otp_code:
            raise HTTPException(status_code=422, detail="Vui lòng nhập mã OTP")
        expected = f"{booking.id:04d}"
        if data.otp_code.strip() != expected and len(data.otp_code.strip()) < 4:
            raise HTTPException(
                status_code=400,
                detail="Mã OTP không đúng. Mã OTP là 4 chữ số cuối mã buổi tập của bạn.",
            )

    confirmation.member_confirmed = True
    confirmation.confirm_method = data.method
    confirmation.confirmed_at = now_local()
    if data.rating:
        confirmation.rating = data.rating
    if data.feedback:
        confirmation.feedback = data.feedback

    # --- Kiểm tra lại điều kiện 1 (phòng trường hợp PT bấm trước khi check-in) ---
    today_start = datetime.combine(date.today(), datetime.min.time())
    gate = (
        db.query(GateCheckin)
        .filter(
            GateCheckin.member_id == member.id,
            GateCheckin.result == GateResult.GRANTED,
            GateCheckin.direction == "in",
            GateCheckin.checkin_time >= today_start,
        )
        .first()
    )
    if gate:
        confirmation.member_checked_in = True
        confirmation.gate_checkin_id = confirmation.gate_checkin_id or gate.id

    both = confirmation.member_checked_in and confirmation.member_confirmed

    deducted = False
    points = 0

    if both:
        # --- Đủ 2 điều kiện -> trừ buổi ---
        purchase = (
            db.query(PTPackagePurchase)
            .filter(PTPackagePurchase.id == confirmation.purchase_id)
            .first()
            if confirmation.purchase_id else _active_purchase(member.id, db)
        )
        if purchase and purchase.sessions_remaining > 0:
            purchase.sessions_used = (purchase.sessions_used or 0) + 1
            purchase.sessions_remaining = max(0, purchase.sessions_remaining - 1)
            if purchase.sessions_remaining == 0:
                purchase.status = PackageStatus.EXHAUSTED
            deducted = True

        confirmation.outcome = SessionOutcome.COMPLETED
        confirmation.session_deducted = True
        confirmation.resolved_at = now_local()

        booking.status = "completed"
        if data.rating:
            booking.rating = data.rating
        if data.feedback:
            booking.trainer_feedback = (
                f"{booking.trainer_feedback or ''}\n[Đánh giá hội viên]: {data.feedback}"
            ).strip()

        # Cập nhật rating trung bình của HLV
        trainer = db.query(Trainer).filter(Trainer.id == booking.trainer_id).first()
        if trainer and data.rating:
            total = (trainer.rating or 5.0) * (trainer.rating_count or 0)
            trainer.rating_count = (trainer.rating_count or 0) + 1
            trainer.rating = round((total + data.rating) / trainer.rating_count, 2)

        points = _award_points(
            member.id, 50, PointKind.WORKOUT_GOAL,
            f"Hoàn thành buổi tập PT #{booking.id}", db,
        )
    else:
        confirmation.outcome = "pending"
        message_blocked = (
            "⚠️ Buổi tập CHƯA được trừ vì hội viên chưa check-in tại cổng phòng gym "
            "trong ngày hôm nay. Theo quy định chống gian lận, cần đủ cả 2 điều kiện."
        )

    db.commit()

    if both:
        purchase_row = (
            db.query(PTPackagePurchase)
            .filter(PTPackagePurchase.id == confirmation.purchase_id).first()
            if confirmation.purchase_id else None
        )
        return {
            "message": (
                f"✅ Xác nhận thành công! Buổi tập đã được ghi nhận. "
                f"Còn lại {purchase_row.sessions_remaining if purchase_row else '—'} buổi."
                + (f" Bạn nhận được {points} điểm thưởng." if points else "")
            ),
            "check_1_member_checked_in": True,
            "check_2_member_confirmed": True,
            "both_confirmed": True,
            "session_deducted": deducted,
            "sessions_remaining": purchase_row.sessions_remaining if purchase_row else None,
            "points_awarded": points,
            "points_balance": points,
        }

    return {
        "message": message_blocked,
        "check_1_member_checked_in": confirmation.member_checked_in,
        "check_2_member_confirmed": confirmation.member_confirmed,
        "both_confirmed": False,
        "session_deducted": False,
        "how_to_fix": (
            "Hãy check-in tại quầy lễ tân hoặc cổng QR của phòng gym, sau đó xác nhận lại "
            "buổi tập. Nếu bạn đã tập nhưng quên check-in, vui lòng liên hệ lễ tân để "
            "được hỗ trợ xác nhận thủ công."
        ),
    }


@router.get("/burn/pending")
def pending_confirmations(
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """Danh sách buổi tập đang chờ hội viên xác nhận (chưa trừ buổi)."""
    trainer = _trainer_of(current_user, db)
    rows = (
        db.query(PTBurnConfirmation)
        .filter(
            PTBurnConfirmation.trainer_id == trainer.id,
            PTBurnConfirmation.member_confirmed == False,
            PTBurnConfirmation.outcome == "pending",
        )
        .order_by(PTBurnConfirmation.trainer_marked_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "booking_id": c.booking_id,
            "member_name": c.booking.member.full_name if c.booking and c.booking.member else None,
            "trainer_marked_at": c.trainer_marked_at,
            "member_checked_in": c.member_checked_in,
            "member_confirmed": c.member_confirmed,
            "status": "Chờ hội viên xác nhận",
        }
        for c in rows
    ]


# ==========================================================================
# ĐỔI PT / DẠY THAY
# ==========================================================================
@router.post("/change-trainer")
def request_trainer_change(
    data: TrainerChangeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hội viên yêu cầu đổi PT (không mất phí); hồ sơ sức khỏe được chuyển nguyên vẹn."""
    member = _member_of(current_user, db)

    if data.kind == "substitution":
        if not data.booking_id:
            raise HTTPException(
                status_code=422, detail="Dạy thay cần chỉ định booking_id của buổi cụ thể"
            )
        booking = db.query(PTBooking).filter(PTBooking.id == data.booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Không tìm thấy buổi tập")
        current_trainer_id = booking.trainer_id
    else:
        if not member.trainer_id:
            raise HTTPException(
                status_code=400, detail="Bạn chưa được gán Huấn luyện viên phụ trách"
            )
        current_trainer_id = member.trainer_id

    req = TrainerChangeRequest(
        member_id=member.id,
        current_trainer_id=current_trainer_id,
        requested_trainer_id=data.requested_trainer_id,
        booking_id=data.booking_id,
        kind=data.kind,
        reason=data.reason,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return {
        "message": (
            "Đã gửi yêu cầu đổi Huấn luyện viên. Quản lý sẽ xử lý trong thời gian sớm nhất. "
            "Toàn bộ hồ sơ sức khỏe, chấn thương và lịch sử mức tạ của bạn sẽ được "
            "chuyển giao nguyên vẹn cho HLV mới."
        ),
        "request_id": req.id,
        "kind": req.kind,
        "fee": 0,
        "fee_note": "Đổi PT hoàn toàn miễn phí.",
    }


@router.post("/change-trainer/{request_id}/approve")
def approve_trainer_change(
    request_id: int,
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """Quản lý duyệt đổi PT / gán dạy thay."""
    req = db.query(TrainerChangeRequest).filter(
        TrainerChangeRequest.id == request_id
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Yêu cầu đã ở trạng thái '{req.status}'")

    member = db.query(Member).filter(Member.id == req.member_id).first()
    old_trainer = db.query(Trainer).filter(Trainer.id == req.current_trainer_id).first()

    if req.kind == "substitution" and req.booking_id:
        # Dạy thay cho MỘT buổi cụ thể
        booking = db.query(PTBooking).filter(PTBooking.id == req.booking_id).first()
        if booking and req.requested_trainer_id:
            booking.trainer_id = req.requested_trainer_id
            slot = booking.slot
            if slot:
                slot.trainer_id = req.requested_trainer_id

        req.status = "approved"
        req.handled_by = current_user.full_name or current_user.username
        req.resolved_at = now_local()
        db.commit()
        new_trainer = db.query(Trainer).filter(
            Trainer.id == req.requested_trainer_id
        ).first()
        return {
            "message": (
                f"Đã gán {new_trainer.full_name if new_trainer else 'HLV'} "
                f"dạy thay cho buổi tập #{req.booking_id}."
            ),
            "kind": "substitution",
            "status": req.status,
        }

    # --- Đổi PT chính thức: chuyển giao toàn bộ hồ sơ ---
    if not req.requested_trainer_id:
        raise HTTPException(
            status_code=422, detail="Cần chỉ định HLV mới để duyệt yêu cầu đổi PT"
        )

    new_trainer = db.query(Trainer).filter(Trainer.id == req.requested_trainer_id).first()
    if not new_trainer:
        raise HTTPException(status_code=404, detail="Không tìm thấy HLV mới")

    if new_trainer.current_trainees >= new_trainer.max_trainees:
        raise HTTPException(
            status_code=400,
            detail=f"HLV {new_trainer.full_name} đã đạt giới hạn học viên",
        )

    if member:
        member.trainer_id = new_trainer.id
        # Gói PT đang hiệu lực cũng chuyển sang HLV mới
        purchase = _active_purchase(member.id, db)
        if purchase:
            purchase.trainer_id = new_trainer.id

    if old_trainer:
        old_trainer.current_trainees = max(0, (old_trainer.current_trainees or 0) - 1)
    new_trainer.current_trainees = (new_trainer.current_trainees or 0) + 1

    req.status = "approved"
    req.handled_by = current_user.full_name or current_user.username
    req.resolved_at = now_local()
    db.commit()

    return {
        "message": (
            f"Đã đổi Huấn luyện viên cho {member.full_name if member else 'hội viên'} "
            f"sang {new_trainer.full_name}. Toàn bộ hồ sơ sức khỏe, phác đồ AI và "
            f"lịch sử mức tạ đã được chuyển giao."
        ),
        "kind": "change",
        "status": req.status,
        "new_trainer_id": new_trainer.id,
        "new_trainer_name": new_trainer.full_name,
        "handover_items": [
            "Hồ sơ sàng lọc PAR-Q và chấn thương",
            "Phiếu đo InBody và lịch sử chỉ số cơ thể",
            "Phác đồ AI đang áp dụng (lịch tập + dinh dưỡng + phục hồi)",
            "Lịch sử mức tạ và ghi chú của HLV cũ",
        ],
    }


# ==========================================================================
# TÍNH LƯƠNG & HOA HỒNG
# ==========================================================================
@router.post("/payroll/generate")
def generate_payroll(
    data: PayrollGenerate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Tính lương & hoa hồng PT cho một tháng.

    Công thức:
        Lương cứng
      + Hoa hồng bán gói  = tổng giá trị gói đã bán x %hoa hồng
      + Thù lao dạy        = số buổi hoàn thành x thù lao/buổi
      + Thưởng 5 sao       = số buổi được 5 sao x mức thưởng
      - Khấu trừ
    """
    period_start = date(data.year, data.month, 1)
    if data.month == 12:
        period_end = date(data.year + 1, 1, 1)
    else:
        period_end = date(data.year, data.month + 1, 1)

    trainers = (
        db.query(Trainer).filter(Trainer.id == data.trainer_id).all()
        if data.trainer_id else
        db.query(Trainer).filter(Trainer.is_active == True).all()
    )
    if not trainers:
        raise HTTPException(status_code=404, detail="Không tìm thấy Huấn luyện viên")

    results = []
    for trainer in trainers:
        # --- Hoa hồng bán gói ---
        sold_total = (
            db.query(func.coalesce(func.sum(PTPackagePurchase.price), 0))
            .filter(
                PTPackagePurchase.trainer_id == trainer.id,
                PTPackagePurchase.created_at >= datetime.combine(period_start, datetime.min.time()),
                PTPackagePurchase.created_at < datetime.combine(period_end, datetime.min.time()),
            )
            .scalar()
        ) or 0

        sold_total = float(sold_total)
        rate = trainer.sale_commission_rate or 0.10
        sale_commission = round(sold_total * rate, 0)

        # --- Thù lao dạy (chỉ tính buổi đã hoàn thành) ---
        delivered = (
            db.query(func.count(PTBooking.id))
            .join(TrainerSlot, PTBooking.slot_id == TrainerSlot.id)
            .filter(
                PTBooking.trainer_id == trainer.id,
                PTBooking.status == "completed",
                TrainerSlot.start_time >= datetime.combine(period_start, datetime.min.time()),
                TrainerSlot.start_time < datetime.combine(period_end, datetime.min.time()),
            )
            .scalar()
        ) or 0

        burn_fee = trainer.burn_fee_per_session or 80000
        delivery_commission = round(delivered * burn_fee, 0)

        # --- Thưởng đánh giá 5 sao ---
        five_star_count = (
            db.query(func.count(PTBurnConfirmation.id))
            .filter(
                PTBurnConfirmation.trainer_id == trainer.id,
                PTBurnConfirmation.rating == 5,
                PTBurnConfirmation.confirmed_at >= datetime.combine(period_start, datetime.min.time()),
                PTBurnConfirmation.confirmed_at < datetime.combine(period_end, datetime.min.time()),
            )
            .scalar()
        ) or 0
        five_star_bonus = round(five_star_count * FIVE_STAR_BONUS, 0)

        base = trainer.base_salary or 0
        total = round(base + sale_commission + delivery_commission + five_star_bonus, 0)

        payroll = (
            db.query(TrainerPayroll)
            .filter(
                TrainerPayroll.trainer_id == trainer.id,
                TrainerPayroll.period_year == data.year,
                TrainerPayroll.period_month == data.month,
            )
            .first()
        )
        if not payroll:
            payroll = TrainerPayroll(
                trainer_id=trainer.id,
                period_year=data.year,
                period_month=data.month,
            )
            db.add(payroll)

        payroll.base_salary = base
        payroll.sale_commission_rate = rate
        payroll.burn_fee_per_session = burn_fee
        payroll.packages_sold_amount = sold_total
        payroll.sale_commission = sale_commission
        payroll.sessions_delivered = delivered
        payroll.delivery_commission = delivery_commission
        payroll.five_star_bonus = five_star_bonus
        payroll.total_pay = total

        results.append({
            "trainer_id": trainer.id,
            "trainer_name": trainer.full_name,
            "base_salary": base,
            "packages_sold_amount": sold_total,
            "commission_rate": f"{round(rate * 100)}%",
            "sale_commission": sale_commission,
            "sessions_delivered": delivered,
            "burn_fee_per_session": burn_fee,
            "delivery_commission": delivery_commission,
            "five_star_sessions": five_star_count,
            "five_star_bonus": five_star_bonus,
            "total_pay": total,
        })

    db.commit()

    return {
        "message": f"Đã tính lương tháng {data.month}/{data.year} cho {len(results)} HLV",
        "period": f"{data.month:02d}/{data.year}",
        "trainers": results,
        "total_payroll": round(sum(r["total_pay"] for r in results), 0),
        "formula": (
            "Lương cứng + (Giá trị gói bán được x %hoa hồng) + "
            "(Số buổi dạy hoàn thành x Thù lao/buổi) + (Số buổi 5 sao x Thưởng)"
        ),
    }


@router.get("/payroll/my")
def my_payroll(
    current_user: User = Depends(require_trainer_or_admin),
    db: Session = Depends(get_db),
):
    """HLV xem bảng lương của mình."""
    trainer = _trainer_of(current_user, db)
    payrolls = (
        db.query(TrainerPayroll)
        .filter(TrainerPayroll.trainer_id == trainer.id)
        .order_by(TrainerPayroll.period_year.desc(), TrainerPayroll.period_month.desc())
        .limit(24)
        .all()
    )
    return {
        "trainer_name": trainer.full_name,
        "base_salary": trainer.base_salary,
        "burn_fee_per_session": trainer.burn_fee_per_session,
        "sale_commission_rate": f"{round((trainer.sale_commission_rate or 0.10) * 100)}%",
        "current_trainees": trainer.current_trainees,
        "rating": trainer.rating,
        "payrolls": [
            {
                "period": f"{p.period_month:02d}/{p.period_year}",
                "base_salary": p.base_salary,
                "sale_commission": p.sale_commission,
                "packages_sold_amount": p.packages_sold_amount,
                "sessions_delivered": p.sessions_delivered,
                "delivery_commission": p.delivery_commission,
                "five_star_bonus": p.five_star_bonus,
                "total_pay": p.total_pay,
                "status": p.status,
            }
            for p in payrolls
        ],
    }