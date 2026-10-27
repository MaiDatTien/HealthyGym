"""Router VẬN HÀNH PHÒNG TẬP — Check-in cổng (QR động), tủ đồ & khăn, POS Pro-Shop."""
from __future__ import annotations

import json
import secrets
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.engagement import LoyaltyPoint, MemberStreak, PointKind
from app.models.interaction import now_local
from app.models.listing import Branch
from app.models.membership import (
    ContractStatus, Lead, LeadStage, MemberWallet, MembershipContract,
    TrialPass, WalletTransaction,
)
from app.models.operations import (
    BookingStatus, ClassBooking, ClassSchedule, DynamicQRToken,
    GateCheckin, GateResult, InventoryTransaction, Locker, LockerAssignment,
    PosOrder, PosOrderItem, Product,
)
from app.models.pt import PTBooking, TrainerSlot
from app.models.user import Member, Trainer, User
from app.schemas.erp import (
    GateScanRequest, InventoryImport, LockerAssignRequest, LockerRentalCreate,
    LockerReturn, PosCheckout, ProductCreate,
)
from app.security import get_current_user, require_operations

router = APIRouter(prefix="/gym-ops", tags=["Gym Operations: Check-in, Locker & POS"])


#: QR động có hiệu lực bao lâu (giây)
QR_TTL_SECONDS = 60
#: Điểm thưởng mỗi lượt check-in
POINTS_PER_CHECKIN = 10


def _member_of(user: User, db: Session) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hội viên")
    return member


def _active_contract(member: Member, db: Session) -> Optional[MembershipContract]:
    return (
        db.query(MembershipContract)
        .filter(
            MembershipContract.member_id == member.id,
            MembershipContract.status.in_([ContractStatus.ACTIVE, ContractStatus.FROZEN]),
        )
        .order_by(MembershipContract.end_date.desc())
        .first()
    )


def _wallet_of(member: Member, db: Session) -> MemberWallet:
    wallet = db.query(MemberWallet).filter(MemberWallet.member_id == member.id).first()
    if not wallet:
        wallet = MemberWallet(member_id=member.id, balance=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


# ==========================================================================
# QR ĐỘNG & CHECK-IN CỔNG (MULTI-CONDITION GATE VALIDATION)
# ==========================================================================
@router.get("/qr/generate")
def generate_dynamic_qr(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Sinh mã QR ĐỘNG đổi mỗi 60 giây — chống chụp màn hình cho người khác mượn thẻ.

    Hội viên mở app để lấy mã mới mỗi lần vào phòng tập. Mã cũ tự hết hiệu lực.
    """
    member = _member_of(current_user, db)
    now = now_local()

    # Vô hiệu hoá các token cũ chưa dùng của hội viên này
    db.query(DynamicQRToken).filter(
        DynamicQRToken.member_id == member.id,
        DynamicQRToken.is_used == False,
    ).update({"is_used": True}, synchronize_session=False)

    token = f"DG-{member.id}-{secrets.token_hex(8).upper()}"
    entry = DynamicQRToken(
        member_id=member.id,
        token=token,
        issued_at=now,
        expires_at=now + timedelta(seconds=QR_TTL_SECONDS),
        is_used=False,
    )
    db.add(entry)
    db.commit()

    contract = _active_contract(member, db)

    return {
        "qr_token": token,
        "issued_at": now,
        "expires_at": entry.expires_at,
        "ttl_seconds": QR_TTL_SECONDS,
        "member_name": member.full_name,
        "tier": member.tier,
        "time_window": member.time_window,
        "status": member.status,
        "note": (
            f"Mã này chỉ có hiệu lực {QR_TTL_SECONDS} giây và tự đổi khi hết hạn. "
            f"Không chia sẻ ảnh chụp màn hình cho người khác — hệ thống sẽ từ chối "
            f"mã đã hết hạn."
        ),
        "benefits": {
            "locker": contract.includes_locker if contract else False,
            "towel": contract.includes_towel if contract else True,
            "sauna": contract.includes_sauna if contract else False,
        } if contract else None,
    }


@router.post("/gate/scan")
def gate_scan(
    data: GateScanRequest,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Quét QR tại cổng — kiểm tra 4 điều kiện trong một lần.

    Điều kiện:
      1. Thẻ có đang Active không? (hết hạn / freeze / chưa kích hoạt)
      2. Chi nhánh hiện tại có nằm trong phạm vi hạng thẻ không?
      3. Giờ hiện tại có hợp lệ không? (thẻ Off-Peak quẹt giờ cao điểm)
      4. Có lịch PT hoặc lớp GroupX sắp diễn ra trong 30 phút tới không?
    """
    now = now_local()
    checks: dict = {}
    warnings: list[str] = []

    # --- Tìm token QR động ---
    entry = (
        db.query(DynamicQRToken)
        .filter(DynamicQRToken.token == data.qr_token.strip())
        .first()
    )

    # --- Hoặc QR tập thử ---
    if not entry:
        trial = (
            db.query(TrialPass)
            .filter(TrialPass.qr_code == data.qr_token.strip())
            .first()
        )
        if trial:
            return _handle_trial_scan(trial, data, current_user, db)

    if not entry:
        raise HTTPException(
            status_code=404, detail="Mã QR không tồn tại hoặc không hợp lệ."
        )

    if entry.is_used:
        raise HTTPException(
            status_code=400,
            detail="Mã QR này đã được sử dụng rồi. Vui lòng tạo mã mới trên app.",
        )

    if entry.expires_at < now:
        raise HTTPException(
            status_code=400,
            detail=f"Mã QR đã hết hạn (mã chỉ có hiệu lực {QR_TTL_SECONDS} giây). "
                   f"Vui lòng làm mới mã trên app của bạn.",
        )

    member = db.query(Member).filter(Member.id == entry.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")

    contract = _active_contract(member, db)
    today = date.today()

    # ============ ĐIỀU KIỆN 1: THẺ CÓ ACTIVE KHÔNG ============
    if member.is_debt_blocked:
        result = GateResult.DENIED_DEBT
        reason = (
            f"Thẻ tạm khóa do công nợ quá hạn {int(member.outstanding_debt):,}đ. "
            f"Vui lòng thanh toán tại quầy lễ tân.".replace(",", ".")
        )
        checks["membership_active"] = False
        checks["debt_blocked"] = True

    elif member.frozen_until and member.frozen_until >= today:
        result = GateResult.DENIED_FROZEN
        reason = f"Thẻ đang bảo lưu đến {member.frozen_until}."
        checks["membership_active"] = False
        checks["frozen"] = True

    elif not member.expire_date or member.expire_date < today:
        result = GateResult.DENIED_EXPIRED
        reason = (
            "Thẻ đã hết hạn." if member.expire_date
            else "Thẻ chưa được kích hoạt."
        )
        checks["membership_active"] = False

    elif member.status not in ("active",):
        result = GateResult.DENIED_INACTIVE
        reason = f"Trạng thái thẻ hiện tại: {member.status}."
        checks["membership_active"] = False

    else:
        checks["membership_active"] = True
        result = GateResult.GRANTED
        reason = None

    # ============ ĐIỀU KIỆN 2: CHI NHÁNH CÓ TRONG PHẠM VI THẺ ============
    branch_ok = True
    if result == GateResult.GRANTED and data.branch_id:
        branch = db.query(Branch).filter(Branch.id == data.branch_id).first()
        chain_scope = contract.plan.branch_scope if contract and contract.plan else "single"

        if chain_scope == "single" and contract and contract.branch_id:
            if contract.branch_id != data.branch_id:
                branch_ok = False
                home = db.query(Branch).filter(Branch.id == contract.branch_id).first()
                result = GateResult.DENIED_BRANCH
                reason = (
                    f"Thẻ hạng Standard chỉ áp dụng tại 1 chi nhánh: "
                    f"{home.name if home else 'chi nhánh đã đăng ký'}. "
                    f"Bạn đang ở {branch.name if branch else 'chi nhánh khác'}. "
                    f"Vui lòng nâng cấp lên hạng Gold/VIP để tập toàn chuỗi."
                )
        checks["branch_valid"] = branch_ok
        checks["branch_scope"] = chain_scope
    else:
        checks["branch_valid"] = True

    # ============ ĐIỀU KIỆN 3: KHUNG GIỜ CÓ HỢP LỆ ============
    off_peak_violation = False
    surcharge = 0.0
    if result == GateResult.GRANTED and member.time_window == "off_peak":
        plan = contract.plan if contract else None
        start_h = plan.off_peak_start_hour if plan else 9
        end_h = plan.off_peak_end_hour if plan else 16
        current_h = now.hour

        if not (start_h <= current_h < end_h):
            off_peak_violation = True
            surcharge = 50000.0
            warnings.append(
                f"⚠️ Thẻ OFF-PEAK chỉ áp dụng từ {start_h:02d}:00 đến {end_h:02d}:00. "
                f"Hiện tại là {current_h:02d}:{now.minute:02d} (giờ cao điểm). "
                f"Vui lòng thu phụ phí {int(surcharge):,}đ để nâng khung giờ, "
                f"hoặc từ chối cho vào.".replace(",", ".")
            )
            checks["time_window_valid"] = False
            checks["off_peak_surcharge"] = surcharge
        else:
            checks["time_window_valid"] = True
    else:
        checks["time_window_valid"] = True

    checks["time_window"] = member.time_window

    # ============ ĐIỀU KIỆN 4: LỊCH HẸN SẮP DIỄN RA ============
    upcoming_pt = None
    upcoming_class = None
    if result == GateResult.GRANTED:
        soon = now + timedelta(minutes=30)

        pt_booking = (
            db.query(PTBooking)
            .join(TrainerSlot, PTBooking.slot_id == TrainerSlot.id)
            .filter(
                PTBooking.member_id == member.id,
                PTBooking.status == "confirmed",
                TrainerSlot.start_time >= now - timedelta(minutes=10),
                TrainerSlot.start_time <= soon,
            )
            .first()
        )
        if pt_booking:
            trainer = db.query(Trainer).filter(
                Trainer.id == pt_booking.trainer_id
            ).first()
            upcoming_pt = {
                "booking_id": pt_booking.id,
                "trainer_id": pt_booking.trainer_id,
                "trainer_name": trainer.full_name if trainer else None,
                "start_time": pt_booking.slot.start_time,
                "minutes_until": int(
                    (pt_booking.slot.start_time - now).total_seconds() // 60
                ),
            }
            warnings.append(
                f"📢 Hội viên {member.full_name} vừa check-in. "
                f"Có lịch tập 1-1 với {trainer.full_name if trainer else 'HLV'} lúc "
                f"{pt_booking.slot.start_time.strftime('%H:%M')}."
            )

        class_booking = (
            db.query(ClassBooking)
            .join(ClassSchedule, ClassBooking.schedule_id == ClassSchedule.id)
            .filter(
                ClassBooking.member_id == member.id,
                ClassBooking.status.in_(["confirmed", "attended"]),
                ClassSchedule.start_time >= now - timedelta(minutes=10),
                ClassSchedule.start_time <= soon,
            )
            .first()
        )
        if class_booking:
            sched = class_booking.schedule
            klass = sched.gym_class if sched else None
            upcoming_class = {
                "booking_id": class_booking.id,
                "class_name": klass.name if klass else None,
                "start_time": sched.start_time if sched else None,
                "spot_code": None,
                "minutes_until": int(
                    (sched.start_time - now).total_seconds() // 60
                ) if sched else 0,
            }
            warnings.append(
                f"📢 Hội viên có lớp '{klass.name if klass else ''}' sắp bắt đầu lúc "
                f"{sched.start_time.strftime('%H:%M') if sched else ''}."
            )

        checks["upcoming_booking"] = bool(upcoming_pt or upcoming_class)

    # ============ GHI NHẬN ============
    entry.is_used = True
    entry.used_at = now

    granted = result == GateResult.GRANTED

    log = GateCheckin(
        member_id=member.id,
        contract_id=contract.id if contract else None,
        branch_id=data.branch_id,
        direction=data.direction,
        result=result,
        reason=reason or "; ".join(warnings) if warnings else None,
        checks_json=json.dumps(checks, ensure_ascii=False),
        is_off_peak_violation=off_peak_violation,
        surcharge_amount=surcharge,
        verified_by=f"QR-{current_user.username}",
        checkin_time=now,
        checkout_time=now if data.direction == "out" else None,
    )
    db.add(log)

    points_awarded = 0
    if granted and data.direction == "in":
        member.last_visit_date = today
        # Cập nhật streak + cộng điểm
        streak = db.query(MemberStreak).filter(
            MemberStreak.member_id == member.id
        ).first()
        if not streak:
            streak = MemberStreak(member_id=member.id)
            db.add(streak)

        if streak.last_activity_date != today:
            streak.total_checkins = (streak.total_checkins or 0) + 1
            streak.this_week_visits = (streak.this_week_visits or 0) + 1

            # Tính chuỗi ngày liên tiếp
            if streak.last_activity_date == today - timedelta(days=1):
                streak.current_day_streak = (streak.current_day_streak or 0) + 1
            else:
                streak.current_day_streak = 1
            streak.longest_day_streak = max(
                streak.longest_day_streak or 0, streak.current_day_streak
            )
            streak.last_activity_date = today

            # Cộng điểm thưởng
            new_balance = (member.loyalty_points or 0) + POINTS_PER_CHECKIN
            member.loyalty_points = new_balance
            member.total_points_earned = (member.total_points_earned or 0) + POINTS_PER_CHECKIN
            db.add(LoyaltyPoint(
                member_id=member.id,
                points=POINTS_PER_CHECKIN,
                balance_after=new_balance,
                kind=PointKind.CHECKIN,
                reference=f"CHECKIN-{log.id if log.id else ''}",
                note="Check-in tại phòng tập",
            ))
            points_awarded = POINTS_PER_CHECKIN

    db.commit()
    db.refresh(log)

    # Thông báo cho HLV nếu có lịch sắp tới
    if upcoming_pt:
        # Ghi chú vào booking để HLV thấy trên dashboard
        booking = db.query(PTBooking).filter(PTBooking.id == upcoming_pt["booking_id"]).first()
        if booking:
            booking.goal_note = (
                f"{booking.goal_note or ''}\n[Check-in {now.strftime('%H:%M')}] "
                f"Học viên đã có mặt tại phòng tập."
            ).strip()
            db.commit()

    return {
        "granted": granted,
        "result": result,
        "member_name": member.full_name,
        "member_id": member.id,
        "tier": member.tier,
        "time_window": member.time_window,
        "expire_date": member.expire_date,
        "reason": reason,
        "checks": checks,
        "checkin_time": log.checkin_time,
        "warnings": warnings,
        "off_peak_violation": off_peak_violation,
        "surcharge_amount": surcharge,
        "upcoming_pt_session": upcoming_pt,
        "upcoming_class": upcoming_class,
        "points_awarded": points_awarded,
        "loyalty_points": member.loyalty_points,
        "day_streak": None,
        "message": (
            f"✅ Check-in thành công! Chúc {member.full_name} buổi tập hiệu quả."
            + (f" (+{points_awarded} điểm thưởng)" if points_awarded else "")
            if granted else
            f"⛔ TỪ CHỐI CHECK-IN: {reason}"
        ),
    }


def _handle_trial_scan(trial, data: GateScanRequest, current_user: User, db: Session) -> dict:
    """Xử lý check-in bằng vé tập thử."""
    now = now_local()
    today = date.today()

    if not trial.otp_verified:
        raise HTTPException(
            status_code=400,
            detail="Vé tập thử chưa được xác thực OTP. Vui lòng xác thực trước khi vào tập.",
        )
    if trial.status == "expired" or trial.end_date < today:
        raise HTTPException(
            status_code=400,
            detail=f"Vé tập thử đã hết hạn ngày {trial.end_date}.",
        )
    if trial.status == "used":
        raise HTTPException(status_code=400, detail="Vé tập thử này đã được sử dụng hết lượt.")

    trial.visits_used = (trial.visits_used or 0) + 1

    log = GateCheckin(
        member_id=None,
        trial_pass_id=trial.id,
        branch_id=data.branch_id,
        direction="in",
        result=GateResult.GRANTED,
        reason=f"Vé tập thử {trial.days} ngày — lượt {trial.visits_used}",
        verified_by=f"TRIAL-{current_user.username}",
        checkin_time=now,
    )
    db.add(log)

    # Cập nhật lead sang "đã đến tập buổi 1"
    lead = db.query(Lead).filter(Lead.trial_pass_id == trial.id).first()
    if lead and lead.stage == LeadStage.NEW:
        lead.stage = LeadStage.SCHEDULED

    if lead and lead.stage == LeadStage.SCHEDULED and trial.visits_used == 1:
        lead.stage = LeadStage.FIRST_VISIT
        lead.first_visit_at = now

    if trial.visits_used >= trial.days:
        trial.status = "used"

    db.commit()

    return {
        "granted": True,
        "result": GateResult.GRANTED,
        "is_trial": True,
        "member_name": trial.full_name,
        "reason": f"Vé tập thử hợp lệ — lượt {trial.visits_used}/{trial.days}",
        "trial_pass": {
            "days": trial.days,
            "visits_used": trial.visits_used,
            "visits_remaining": max(0, trial.days - trial.visits_used),
            "end_date": trial.end_date,
        },
        "warnings": [
            f"🎁 Khách tập thử {trial.full_name} — đây là cơ hội tư vấn chốt gói! "
            f"Hãy mời khách đo InBody và trải nghiệm AI Coach."
        ],
        "sales_hint": (
            "Luồng CRM: cập nhật lead sang 'Đã đến tập buổi 1', sau đó mời đo InBody "
            "để chuyển sang 'Đã đo InBody & Tư vấn AI'."
        ),
        "message": f"✅ Cho vào tập thử. Còn {max(0, trial.days - trial.visits_used)} lượt.",
    }


@router.get("/gate/history")
def gate_history(
    member_id: Optional[int] = None,
    result_filter: Optional[str] = Query(None, alias="result"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Lịch sử ra/vào cổng."""
    query = db.query(GateCheckin)
    if member_id:
        query = query.filter(GateCheckin.member_id == member_id)
    if result_filter:
        query = query.filter(GateCheckin.result == result_filter)

    logs = query.order_by(GateCheckin.checkin_time.desc()).limit(limit).all()

    denied_count = (
        db.query(func.count(GateCheckin.id))
        .filter(
            GateCheckin.result != GateResult.GRANTED,
            GateCheckin.checkin_time >= datetime.combine(date.today(), datetime.min.time()),
        )
        .scalar()
        or 0
    )

    return {
        "today_denied_count": denied_count,
        "total_returned": len(logs),
        "logs": [
            {
                "id": g.id,
                "member_id": g.member_id,
                "member_name": g.member.full_name if g.member else None,
                "direction": g.direction,
                "result": g.result,
                "reason": g.reason,
                "is_off_peak_violation": g.is_off_peak_violation,
                "surcharge_amount": g.surcharge_amount,
                "verified_by": g.verified_by,
                "checkin_time": g.checkin_time,
            }
            for g in logs
        ],
    }


# ==========================================================================
# TỦ ĐỒ & KHĂN TẬP
# ==========================================================================
@router.post("/lockers/assign")
def assign_locker(
    data: LockerAssignRequest,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Lễ tân gán tủ đồ và phát khăn khi hội viên check-in."""
    member = db.query(Member).filter(Member.id == data.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")

    # Hội viên đang giữ tủ chưa trả?
    existing = (
        db.query(LockerAssignment)
        .filter(
            LockerAssignment.member_id == member.id,
            LockerAssignment.returned_at == None,
            LockerAssignment.is_monthly_rental == False,
        )
        .first()
    )
    if existing:
        locker = existing.locker
        raise HTTPException(
            status_code=400,
            detail=f"Hội viên đang giữ tủ {locker.code if locker else '?'} chưa trả. "
                   f"Vui lòng thu hồi tủ trước khi cấp tủ mới.",
        )

    # Chọn tủ trống
    if data.locker_id:
        locker = db.query(Locker).filter(Locker.id == data.locker_id).first()
        if not locker:
            raise HTTPException(status_code=404, detail="Không tìm thấy tủ")
        if not locker.is_available:
            raise HTTPException(status_code=409, detail=f"Tủ {locker.code} đang được sử dụng")
    else:
        query = db.query(Locker).filter(
            Locker.is_available == True,
            Locker.kind == "daily",
        )
        if data.zone:
            query = query.filter(Locker.zone == data.zone)
        locker = query.order_by(Locker.code.asc()).first()
        if not locker:
            raise HTTPException(
                status_code=400,
                detail=f"Không còn tủ trống"
                       + (f" ở khu {data.zone}" if data.zone else "") + ".",
            )

    locker.is_available = False

    assignment = LockerAssignment(
        locker_id=locker.id,
        member_id=member.id,
        towels_issued=data.towels,
        towels_returned=0,
        key_returned=False,
        assigned_by=current_user.full_name or current_user.username,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return {
        "message": (
            f"Đã cấp tủ {locker.code} ({locker.zone}) và {data.towels} khăn cho "
            f"{member.full_name}."
        ),
        "assignment_id": assignment.id,
        "locker_code": locker.code,
        "locker_zone": locker.zone,
        "towels_issued": data.towels,
        "reminder": (
            "Nhắc hội viên trả chìa khóa tủ và khăn khi ra về. "
            "Nếu mất chìa khóa, ghi nhận khoản phạt vào phiếu thu hồi."
        ),
    }


@router.post("/lockers/{assignment_id}/return")
def return_locker(
    assignment_id: int,
    data: LockerReturn,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Thu hồi tủ và khăn khi hội viên ra về; ghi nhận phạt nếu thiếu."""
    assignment = (
        db.query(LockerAssignment).filter(LockerAssignment.id == assignment_id).first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu cấp tủ")
    if assignment.returned_at:
        raise HTTPException(status_code=400, detail="Phiếu này đã được thu hồi rồi")

    locker = db.query(Locker).filter(Locker.id == assignment.locker_id).first()
    member = db.query(Member).filter(Member.id == assignment.member_id).first()

    assignment.towels_returned = data.towels_returned
    assignment.key_returned = data.key_returned
    assignment.returned_at = now_local()

    # Tự động tính phạt
    auto_penalty = 0.0
    penalty_notes: list[str] = []

    missing_towels = (assignment.towels_issued or 0) - data.towels_returned
    if missing_towels > 0:
        auto_penalty += missing_towels * 100000
        penalty_notes.append(f"Thiếu {missing_towels} khăn x 100.000đ")

    if not data.key_returned:
        auto_penalty += 200000
        penalty_notes.append("Mất chìa khóa tủ: 200.000đ")

    total_penalty = auto_penalty + data.penalty_amount
    assignment.penalty_amount = total_penalty
    assignment.penalty_reason = data.penalty_reason or (
        "; ".join(penalty_notes) if penalty_notes else None
    )

    if locker:
        locker.is_available = True

    # Cộng vào công nợ hội viên nếu có phạt
    if total_penalty > 0 and member:
        member.outstanding_debt = round((member.outstanding_debt or 0) + total_penalty, 0)

    db.commit()

    return {
        "message": (
            f"Đã thu hồi tủ"
            + (f" {locker.code}" if locker else "")
            + f". Khăn trả: {data.towels_returned}/{assignment.towels_issued}."
            + (f" Phạt: {int(total_penalty):,}đ đã ghi vào hồ sơ hội viên."
               .replace(",", ".") if total_penalty > 0 else " Không phát sinh phạt.")
        ),
        "locker_returned": locker.code if locker else None,
        "towels_issued": assignment.towels_issued,
        "towels_returned": data.towels_returned,
        "key_returned": data.key_returned,
        "penalty_amount": total_penalty,
        "penalty_detail": penalty_notes,
        "member_debt_total": member.outstanding_debt if member else 0,
    }


@router.post("/lockers/rent")
def rent_private_locker(
    data: LockerRentalCreate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Cho thuê tủ cố định theo tháng (VIP Private Locker)."""
    member = db.query(Member).filter(Member.id == data.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")

    existing = (
        db.query(LockerAssignment)
        .filter(
            LockerAssignment.member_id == member.id,
            LockerAssignment.is_monthly_rental == True,
            LockerAssignment.rental_end >= date.today(),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Hội viên đã thuê tủ cố định đến {existing.rental_end}.",
        )

    locker = (
        db.query(Locker)
        .filter(
            Locker.is_available == True,
            Locker.kind == "private",
            Locker.zone == data.zone,
        )
        .order_by(Locker.code.asc())
        .first()
    )
    if not locker:
        raise HTTPException(
            status_code=400, detail=f"Không còn tủ cố định trống ở khu {data.zone}."
        )

    locker.is_available = False
    start = date.today()
    end = start + timedelta(days=30 * data.months)
    fee = (locker.monthly_fee or 200000) * data.months

    assignment = LockerAssignment(
        locker_id=locker.id,
        member_id=member.id,
        is_monthly_rental=True,
        rental_start=start,
        rental_end=end,
        towels_issued=0,
        assigned_by=current_user.full_name or current_user.username,
    )
    db.add(assignment)

    member.has_private_locker = True
    member.outstanding_debt = round((member.outstanding_debt or 0) + fee, 0)

    db.commit()
    db.refresh(assignment)

    return {
        "message": (
            f"Đã cho thuê tủ cố định {locker.code} ({data.zone}) cho {member.full_name} "
            f"trong {data.months} tháng. Phí: {int(fee):,}đ.".replace(",", ".")
        ),
        "assignment_id": assignment.id,
        "locker_code": locker.code,
        "rental_start": start,
        "rental_end": end,
        "months": data.months,
        "monthly_fee": locker.monthly_fee,
        "total_fee": fee,
    }


@router.get("/lockers/status")
def locker_status(
    branch_id: Optional[int] = None,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Tình trạng tủ đồ: trống, đang dùng, tủ cố định đã cho thuê."""
    query = db.query(Locker)
    if branch_id:
        query = query.filter(Locker.branch_id == branch_id)
    lockers = query.order_by(Locker.code.asc()).all()

    in_use = (
        db.query(LockerAssignment)
        .filter(LockerAssignment.returned_at == None, LockerAssignment.is_monthly_rental == False)
        .all()
    )
    in_use_map = {a.locker_id: a for a in in_use}

    return {
        "total": len(lockers),
        "available": sum(1 for l in lockers if l.is_available),
        "occupied": len(in_use_map),
        "lockers": [
            {
                "code": l.code,
                "zone": l.zone,
                "kind": l.kind,
                "is_available": l.is_available,
                "monthly_fee": l.monthly_fee if l.kind == "private" else None,
                "holder": (
                    in_use_map[l.id].member.full_name
                    if l.id in in_use_map and in_use_map[l.id].member else None
                ),
                "assigned_at": in_use_map[l.id].assigned_at if l.id in in_use_map else None,
            }
            for l in lockers
        ],
    }


# ==========================================================================
# POS & KHO PRO-SHOP
# ==========================================================================
@router.get("/products")
def list_products(
    category: Optional[str] = None,
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
):
    """Danh mục sản phẩm Pro-Shop kèm cảnh báo tồn kho."""
    query = db.query(Product).filter(Product.is_active == True)
    if category:
        query = query.filter(Product.category == category)
    products = query.order_by(Product.name.asc()).all()

    today = date.today()
    result = []
    for p in products:
        is_low = p.stock_quantity <= p.low_stock_threshold
        if low_stock_only and not is_low:
            continue

        days_to_expiry = (p.expiry_date - today).days if p.expiry_date else None

        result.append({
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "brand": p.brand,
            "unit": p.unit,
            "price": p.price,
            "serving_price": p.serving_price,
            "servings_per_unit": p.servings_per_unit,
            "cost_price": p.cost_price,
            "stock_quantity": p.stock_quantity,
            "low_stock_threshold": p.low_stock_threshold,
            "is_low_stock": is_low,
            "expiry_date": p.expiry_date,
            "days_to_expiry": days_to_expiry,
            "expiry_warning": (
                f"⚠️ Sắp hết hạn trong {days_to_expiry} ngày!"
                if days_to_expiry is not None and days_to_expiry <= 30
                else None
            ),
            "can_sell_by_serving": p.servings_per_unit > 0 and p.serving_price > 0,
        })
    return result


@router.post("/products")
def create_product(
    data: ProductCreate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Thêm sản phẩm mới vào Pro-Shop."""
    if db.query(Product).filter(Product.sku == data.sku).first():
        raise HTTPException(status_code=400, detail=f"SKU '{data.sku}' đã tồn tại")

    product = Product(**data.model_dump(), is_active=True)
    db.add(product)
    db.flush()

    if data.stock_quantity > 0:
        db.add(InventoryTransaction(
            product_id=product.id,
            kind="import",
            quantity=data.stock_quantity,
            stock_after=data.stock_quantity,
            unit_cost=data.cost_price,
            note="Tồn kho ban đầu",
            performed_by=current_user.full_name or current_user.username,
        ))

    db.commit()
    db.refresh(product)
    return {
        "message": f"Đã thêm sản phẩm '{product.name}' (SKU {product.sku})",
        "product_id": product.id,
    }


@router.post("/inventory/import")
def import_inventory(
    data: InventoryImport,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Nhập kho hàng hóa."""
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")

    product.stock_quantity = round((product.stock_quantity or 0) + data.quantity, 1)
    if data.unit_cost > 0:
        product.cost_price = data.unit_cost

    db.add(InventoryTransaction(
        product_id=product.id,
        kind="import",
        quantity=data.quantity,
        stock_after=product.stock_quantity,
        unit_cost=data.unit_cost,
        note=data.note,
        performed_by=current_user.full_name or current_user.username,
    ))
    db.commit()

    return {
        "message": (
            f"Đã nhập {data.quantity} {product.unit} '{product.name}'. "
            f"Tồn kho mới: {product.stock_quantity} {product.unit}."
        ),
        "product_id": product.id,
        "stock_quantity": product.stock_quantity,
        "inventory_value": round(product.stock_quantity * (product.cost_price or 0), 0),
    }


@router.post("/pos/checkout")
def pos_checkout(
    data: PosCheckout,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Bán hàng tại quầy. Hỗ trợ tiền mặt, chuyển khoản, ví trả trước, bán lẻ từng muỗng."""
    member = None
    if data.member_id:
        member = db.query(Member).filter(Member.id == data.member_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")

    order_code = f"POS-{now_local().strftime('%y%m%d')}-{secrets.token_hex(2).upper()}"

    subtotal = 0.0
    total_cost = 0.0
    items_payload: list[dict] = []
    low_stock_warnings: list[str] = []

    for item in data.items:
        product = db.query(Product).filter(
            Product.id == item.product_id, Product.is_active == True
        ).first()
        if not product:
            raise HTTPException(
                status_code=404, detail=f"Không tìm thấy sản phẩm ID {item.product_id}"
            )

        # --- Bán lẻ theo muỗng ---
        if item.by_serving:
            if product.servings_per_unit <= 0 or product.serving_price <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm '{product.name}' không hỗ trợ bán lẻ theo muỗng.",
                )
            unit_price = product.serving_price
            unit_label = "muỗng"
            # Trừ kho theo tỷ lệ (1 muỗng = 1/servings_per_unit hũ)
            stock_deduct = round(item.quantity / product.servings_per_unit, 3)
            cost_deduct = (product.cost_price or 0) * stock_deduct
        else:
            unit_price = product.price
            unit_label = product.unit
            stock_deduct = item.quantity
            cost_deduct = (product.cost_price or 0) * item.quantity

        if product.stock_quantity < stock_deduct:
            raise HTTPException(
                status_code=400,
                detail=f"'{product.name}' không đủ tồn kho. "
                       f"Còn {product.stock_quantity} {product.unit}, "
                       f"cần {stock_deduct} {product.unit}.",
            )

        line_total = round(unit_price * item.quantity, 0)
        subtotal += line_total
        total_cost += cost_deduct

        product.stock_quantity = round(product.stock_quantity - stock_deduct, 3)

        if product.stock_quantity <= product.low_stock_threshold:
            low_stock_warnings.append(
                f"⚠️ '{product.name}' sắp hết hàng: còn {product.stock_quantity} {product.unit}"
            )

        items_payload.append({
            "product": product,
            "quantity": item.quantity,
            "unit": unit_label,
            "unit_price": unit_price,
            "cost_price": cost_deduct / item.quantity if item.quantity else 0,
            "line_total": line_total,
            "stock_deduct": stock_deduct,
        })

    discount = min(data.discount_amount, subtotal)
    total_amount = round(subtotal - discount, 0)
    profit = round(total_amount - total_cost, 0)

    # --- Thanh toán bằng ví ---
    wallet_txn_id = None
    if data.payment_method == "wallet":
        if not member:
            raise HTTPException(
                status_code=400,
                detail="Thanh toán bằng ví yêu cầu chọn hội viên.",
            )
        wallet = _wallet_of(member, db)
        if wallet.balance < total_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Số dư ví không đủ. Hiện có {int(wallet.balance):,}đ, "
                       f"cần {int(total_amount):,}đ.".replace(",", "."),
            )
        wallet.balance = round(wallet.balance - total_amount, 0)
        wallet.total_spent = round((wallet.total_spent or 0) + total_amount, 0)

        txn = WalletTransaction(
            wallet_id=wallet.id,
            member_id=member.id,
            amount=-total_amount,
            balance_after=wallet.balance,
            kind="purchase",
            reference=order_code,
            note=f"Mua hàng tại quầy ({len(data.items)} mặt hàng)",
        )
        db.add(txn)
        db.flush()
        wallet_txn_id = txn.id

    order = PosOrder(
        order_code=order_code,
        branch_id=data.branch_id,
        member_id=member.id if member else None,
        customer_name=data.customer_name or (member.full_name if member else "Khách vãng lai"),
        subtotal=round(subtotal, 0),
        discount_amount=discount,
        total_amount=total_amount,
        total_cost=round(total_cost, 0),
        profit=profit,
        payment_method=data.payment_method,
        wallet_txn_id=wallet_txn_id,
        status="completed",
        cashier=current_user.full_name or current_user.username,
        note=data.note,
    )
    db.add(order)
    db.flush()

    for payload in items_payload:
        product = payload["product"]
        db.add(PosOrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=payload["quantity"],
            unit=payload["unit"],
            unit_price=payload["unit_price"],
            cost_price=round(payload["cost_price"], 0),
            line_total=payload["line_total"],
        ))
        db.add(InventoryTransaction(
            product_id=product.id,
            kind="export",
            quantity=-payload["stock_deduct"],
            stock_after=product.stock_quantity,
            reference=order_code,
            note=f"Bán tại quầy cho {order.customer_name}",
            performed_by=current_user.full_name or current_user.username,
        ))

    # Cộng điểm cho hội viên theo giá trị đơn hàng
    points_awarded = 0
    if member:
        points_awarded = int(total_amount // 10000)
        if points_awarded > 0:
            new_balance = (member.loyalty_points or 0) + points_awarded
            member.loyalty_points = new_balance
            member.total_points_earned = (member.total_points_earned or 0) + points_awarded
            db.add(LoyaltyPoint(
                member_id=member.id,
                points=points_awarded,
                balance_after=new_balance,
                kind=PointKind.PURCHASE,
                reference=order_code,
                note=f"Mua hàng {int(total_amount):,}đ".replace(",", "."),
            ))

    db.commit()
    db.refresh(order)

    return {
        "message": (
            f"✅ Thanh toán thành công {int(total_amount):,}đ "
            f"({len(data.items)} mặt hàng).".replace(",", ".")
            + (f" Khách nhận {points_awarded} điểm thưởng." if points_awarded else "")
        ),
        "order_id": order.id,
        "order_code": order_code,
        "subtotal": round(subtotal, 0),
        "discount_amount": discount,
        "total_amount": total_amount,
        "profit": profit,
        "payment_method": data.payment_method,
        "wallet_balance_after": _wallet_of(member, db).balance if member and data.payment_method == "wallet" else None,
        "points_awarded": points_awarded,
        "low_stock_warnings": low_stock_warnings,
    }


@router.get("/pos/orders")
def list_pos_orders(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Lịch sử đơn hàng POS."""
    since = now_local() - timedelta(days=days)
    orders = (
        db.query(PosOrder)
        .filter(PosOrder.created_at >= since)
        .order_by(PosOrder.created_at.desc())
        .limit(200)
        .all()
    )

    total_revenue = sum(o.total_amount or 0 for o in orders)
    total_profit = sum(o.profit or 0 for o in orders)

    return {
        "period_days": days,
        "total_orders": len(orders),
        "total_revenue": round(total_revenue, 0),
        "total_profit": round(total_profit, 0),
        "margin_percent": round(total_profit / total_revenue * 100, 1) if total_revenue else 0,
        "orders": [
            {
                "id": o.id,
                "order_code": o.order_code,
                "customer_name": o.customer_name,
                "total_amount": o.total_amount,
                "profit": o.profit,
                "payment_method": o.payment_method,
                "cashier": o.cashier,
                "item_count": len(o.items),
                "created_at": o.created_at,
            }
            for o in orders
        ],
    }


@router.get("/inventory/low-stock")
def low_stock_report(
    current_user: User = Depends(require_operations), db: Session = Depends(get_db)
):
    """Báo cáo hàng sắp hết và sắp hết hạn."""
    products = db.query(Product).filter(Product.is_active == True).all()
    today = date.today()

    low_stock = []
    expiring_soon = []
    total_inventory_value = 0.0

    for p in products:
        total_inventory_value += (p.stock_quantity or 0) * (p.cost_price or 0)

        if p.stock_quantity <= p.low_stock_threshold:
            low_stock.append({
                "product_id": p.id,
                "name": p.name,
                "sku": p.sku,
                "stock_quantity": p.stock_quantity,
                "threshold": p.low_stock_threshold,
                "unit": p.unit,
                "suggested_order": max(10, (p.low_stock_threshold or 5) * 3 - (p.stock_quantity or 0)),
            })

        if p.expiry_date:
            days = (p.expiry_date - today).days
            if days <= 60:
                expiring_soon.append({
                    "product_id": p.id,
                    "name": p.name,
                    "expiry_date": p.expiry_date,
                    "days_to_expiry": days,
                    "stock_quantity": p.stock_quantity,
                    "is_expired": days < 0,
                })

    expiring_soon.sort(key=lambda x: x["days_to_expiry"])

    return {
        "total_inventory_value": round(total_inventory_value, 0),
        "low_stock_count": len(low_stock),
        "expiring_count": len(expiring_soon),
        "low_stock": low_stock,
        "expiring_soon": expiring_soon,
        "advice": (
            "Sản phẩm sắp hết hạn nên được xả hàng bằng khuyến mãi hoặc dùng làm "
            "quà tặng kèm khi hội viên gia hạn gói."
            if expiring_soon else None
        ),
    }