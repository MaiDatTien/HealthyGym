"""Router VÒNG ĐỜI HỢP ĐỒNG HỘI VIÊN.

Bao gồm: hợp đồng, bảo lưu, chuyển nhượng, nâng cấp (prorated),
công nợ/trả góp, leads tập thử (CRM) và ví trả trước.
"""
from __future__ import annotations

import random
import secrets
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interaction import Voucher, now_local
from app.models.listing import Branch, MembershipPlan
from app.models.membership import (
    ContractStatus, FreezeRequest, Installment, Lead, LeadStage,
    MemberWallet, MembershipContract, PaymentStatus, TierLevel,
    TransferRequest, TrialPass, UpgradeRequest, WalletTransaction,
)
from app.models.user import Member, Role, User
from app.schemas.erp import (
    ContractCreate, FreezeApproval, FreezeCreate, InstallmentPay,
    LeadCreate, LeadUpdate, OTPVerify, TransferCreate, TrialPassRequest,
    UpgradeCreate, WalletTopup,
)
from app.security import get_current_user, require_operations

router = APIRouter(prefix="/memberships", tags=["Membership Lifecycle"])


# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------
def _member(user: User, db: Session) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hội viên")
    return member


def _generate_contract_code(db: Session) -> str:
    """Sinh mã hợp đồng dạng HD-YYYYMM-XXXX."""
    stamp = now_local().strftime("%Y%m")
    for _ in range(20):
        code = f"HD-{stamp}-{secrets.randbelow(9000) + 1000}"
        if not db.query(MembershipContract).filter(
            MembershipContract.contract_code == code
        ).first():
            return code
    return f"HD-{stamp}-{secrets.token_hex(3).upper()}"


def _apply_tier_benefits(contract: MembershipContract, plan: MembershipPlan, tier: str) -> None:
    """Áp dụng quyền lợi theo hạng thẻ."""
    contract.includes_locker = bool(plan.includes_locker) or tier == TierLevel.VIP
    contract.includes_towel = bool(plan.includes_towel)
    contract.includes_sauna = bool(plan.includes_sauna) or tier == TierLevel.VIP
    contract.guest_passes_month = plan.guest_passes_month or (
        4 if tier == TierLevel.VIP else (2 if tier == TierLevel.GOLD else 0)
    )


def _sync_member_from_contract(member: Member, contract: MembershipContract) -> None:
    """Đồng bộ trạng thái nhanh trên hồ sơ hội viên từ hợp đồng."""
    member.current_plan_id = contract.plan_id
    member.expire_date = contract.end_date
    member.tier = contract.tier
    member.time_window = contract.time_window
    member.has_private_locker = contract.includes_locker


def _active_contract(member: Member, db: Session) -> Optional[MembershipContract]:
    """Hợp đồng đang hiệu lực của hội viên."""
    return (
        db.query(MembershipContract)
        .filter(
            MembershipContract.member_id == member.id,
            MembershipContract.status.in_([ContractStatus.ACTIVE, ContractStatus.FROZEN]),
        )
        .order_by(MembershipContract.end_date.desc())
        .first()
    )


def _current_year_freeze_days(member_id: int, db: Session) -> int:
    """Tổng số ngày bảo lưu đã dùng trong năm dương lịch hiện tại."""
    year_start = date(date.today().year, 1, 1)
    total = (
        db.query(func.coalesce(func.sum(FreezeRequest.days), 0))
        .filter(
            FreezeRequest.member_id == member_id,
            FreezeRequest.status.in_(["approved", "completed"]),
            FreezeRequest.start_date >= year_start,
        )
        .scalar()
    )
    return int(total or 0)


def _recalc_installments_status(contract: MembershipContract, db: Session) -> None:
    """Cập nhật trạng thái thanh toán của hợp đồng từ các kỳ."""
    installments = (
        db.query(Installment).filter(Installment.contract_id == contract.id).all()
    )
    if not installments:
        return

    paid_total = sum(i.paid_amount or 0 for i in installments)
    contract.paid_amount = round(paid_total, 0)

    today = date.today()
    overdue = [i for i in installments if i.status != PaymentStatus.PAID and i.due_date < today]
    for inst in installments:
        if inst.paid_amount >= inst.amount:
            inst.status = PaymentStatus.PAID
        elif inst.paid_amount > 0:
            inst.status = PaymentStatus.PARTIAL
        elif inst.due_date < today:
            inst.status = PaymentStatus.OVERDUE

    if contract.paid_amount >= contract.final_price:
        contract.payment_status = PaymentStatus.PAID
    elif contract.paid_amount > 0:
        contract.payment_status = PaymentStatus.PARTIAL
    else:
        contract.payment_status = PaymentStatus.UNPAID

    if overdue and contract.payment_status != PaymentStatus.PAID:
        contract.payment_status = PaymentStatus.OVERDUE


def _sync_debt_block(member: Member, db: Session) -> float:
    """Tính công nợ quá hạn và bật/tắt cờ khóa thẻ do nợ."""
    today = date.today()
    overdue_total = (
        db.query(func.coalesce(func.sum(Installment.amount - Installment.paid_amount), 0))
        .filter(
            Installment.member_id == member.id,
            Installment.due_date < today,
            Installment.status != PaymentStatus.PAID,
        )
        .scalar()
    )
    outstanding = (
        db.query(func.coalesce(func.sum(Installment.amount - Installment.paid_amount), 0))
        .filter(
            Installment.member_id == member.id,
            Installment.status != PaymentStatus.PAID,
        )
        .scalar()
    )
    member.outstanding_debt = round(float(outstanding or 0), 0)
    member.is_debt_blocked = float(overdue_total or 0) > 0
    return round(float(overdue_total or 0), 0)


def _wallet_for(member: Member, db: Session) -> MemberWallet:
    """Lấy hoặc tạo ví trả trước cho hội viên."""
    wallet = db.query(MemberWallet).filter(MemberWallet.member_id == member.id).first()
    if not wallet:
        wallet = MemberWallet(member_id=member.id, balance=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


# ==========================================================================
# HỢP ĐỒNG
# ==========================================================================
@router.post("/contracts")
def create_contract(
    data: ContractCreate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Tạo hợp đồng mới (mở thẻ / gia hạn). Hỗ trợ trả góp và đặt cọc."""
    member = db.query(Member).filter(Member.id == data.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")

    plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == data.plan_id, MembershipPlan.is_active == True
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Gói tập không tồn tại hoặc đã ngừng bán")

    discount = 0.0
    applied_code = None
    if data.voucher_code and data.voucher_code.strip():
        code = data.voucher_code.strip().upper()
        voucher = db.query(Voucher).filter(
            Voucher.code == code, Voucher.is_active == True
        ).first()
        if not voucher:
            raise HTTPException(status_code=400, detail=f"Mã giảm giá '{code}' không hợp lệ")
        if voucher.valid_until and voucher.valid_until < now_local():
            raise HTTPException(status_code=400, detail=f"Mã giảm giá '{code}' đã hết hạn")
        discount = min(plan.price * voucher.discount_percent / 100.0,
                       voucher.max_discount_amount)
        applied_code = code

    final_price = max(0.0, plan.price - discount)

    # Ngày bắt đầu: gia hạn nối tiếp nếu thẻ cũ còn hạn
    today = date.today()
    start = data.start_date or today
    existing = _active_contract(member, db)
    if not data.start_date and existing and existing.end_date > today:
        start = existing.end_date

    end = start + timedelta(days=plan.duration_days)

    contract = MembershipContract(
        contract_code=_generate_contract_code(db),
        member_id=member.id,
        plan_id=plan.id,
        branch_id=data.branch_id or member.home_branch_id,
        tier=data.tier or plan.tier,
        time_window=data.time_window or plan.time_window,
        start_date=start,
        end_date=end,
        duration_days=plan.duration_days,
        list_price=plan.price,
        discount_amount=discount,
        final_price=final_price,
        status=ContractStatus.ACTIVE,
        is_renewal=bool(existing),
        previous_contract_id=existing.id if existing else None,
        sold_by=data.sold_by or current_user.full_name or current_user.username,
        note=data.note,
    )
    _apply_tier_benefits(contract, plan, contract.tier)
    db.add(contract)
    db.flush()

    # --- Sinh lịch thanh toán ---
    if data.installment_count > 0:
        down = min(data.down_payment, final_price)
        remaining = max(0.0, final_price - down)
        periods = data.installment_count
        per_period = round(remaining / periods, 0) if periods else remaining

        if down > 0:
            db.add(Installment(
                contract_id=contract.id, member_id=member.id, sequence=1,
                amount=down, due_date=today,
                paid_amount=down, paid_at=now_local(),
                status=PaymentStatus.PAID, method=data.payment_method,
                note="Đặt cọc giữ chỗ",
            ))

        start_seq = 2 if down > 0 else 1
        for i in range(periods):
            amount = per_period
            # Kỳ cuối hấp thụ phần làm tròn
            if i == periods - 1:
                already = down + per_period * (periods - 1)
                amount = round(max(0.0, final_price - already), 0)
            db.add(Installment(
                contract_id=contract.id, member_id=member.id,
                sequence=start_seq + i, amount=amount,
                due_date=today + timedelta(days=30 * (i + 1)),
                status=PaymentStatus.UNPAID,
                note=f"Kỳ {start_seq + i}/{periods + (1 if down > 0 else 0)}",
            ))
    else:
        db.add(Installment(
            contract_id=contract.id, member_id=member.id, sequence=1,
            amount=final_price, due_date=today,
            paid_amount=final_price, paid_at=now_local(),
            status=PaymentStatus.PAID, method=data.payment_method,
            note="Thanh toán một lần",
        ))

    _sync_member_from_contract(member, contract)
    member.status = "active"
    member.frozen_until = None

    _recalc_installments_status(contract, db)
    _sync_debt_block(member, db)
    db.commit()
    db.refresh(contract)

    return {
        "message": (
            f"Đã tạo hợp đồng {contract.contract_code} cho {member.full_name}. "
            f"Hạn thẻ đến {contract.end_date}."
        ),
        "contract_id": contract.id,
        "contract_code": contract.contract_code,
        "final_price": final_price,
        "discount_amount": discount,
        "voucher_code": applied_code,
        "payment_status": contract.payment_status,
        "start_date": contract.start_date,
        "end_date": contract.end_date,
        "tier": contract.tier,
        "time_window": contract.time_window,
        "benefits": {
            "locker": contract.includes_locker,
            "towel": contract.includes_towel,
            "sauna": contract.includes_sauna,
            "guest_passes_month": contract.guest_passes_month,
        },
    }


@router.get("/contracts/my")
def my_contracts(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Danh sách hợp đồng của hội viên đang đăng nhập."""
    member = _member(current_user, db)
    contracts = (
        db.query(MembershipContract)
        .filter(MembershipContract.member_id == member.id)
        .order_by(MembershipContract.created_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "contract_code": c.contract_code,
            "plan_name": c.plan.name if c.plan else None,
            "tier": c.tier,
            "time_window": c.time_window,
            "status": c.status,
            "start_date": c.start_date,
            "end_date": c.end_date,
            "days_remaining": c.days_remaining,
            "final_price": c.final_price,
            "paid_amount": c.paid_amount,
            "payment_status": c.payment_status,
            "prorated_value": c.prorated_value,
            "freeze_days_used": c.freeze_days_used,
            "benefits": {
                "locker": c.includes_locker,
                "towel": c.includes_towel,
                "sauna": c.includes_sauna,
                "guest_passes_month": c.guest_passes_month,
            },
        }
        for c in contracts
    ]


@router.get("/contracts/{contract_id}")
def contract_detail(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chi tiết hợp đồng kèm lịch thanh toán."""
    contract = db.query(MembershipContract).filter(
        MembershipContract.id == contract_id
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Không tìm thấy hợp đồng")

    # Hội viên chỉ được xem hợp đồng của chính mình
    if Role.normalize(current_user.role) == Role.MEMBER:
        member = _member(current_user, db)
        if contract.member_id != member.id:
            raise HTTPException(status_code=403, detail="Bạn không có quyền xem hợp đồng này")

    installments = (
        db.query(Installment)
        .filter(Installment.contract_id == contract.id)
        .order_by(Installment.sequence.asc())
        .all()
    )

    return {
        "contract_code": contract.contract_code,
        "member_name": contract.member.full_name if contract.member else None,
        "plan_name": contract.plan.name if contract.plan else None,
        "status": contract.status,
        "tier": contract.tier,
        "time_window": contract.time_window,
        "start_date": contract.start_date,
        "end_date": contract.end_date,
        "days_remaining": contract.days_remaining,
        "list_price": contract.list_price,
        "discount_amount": contract.discount_amount,
        "prorated_credit": contract.prorated_credit,
        "final_price": contract.final_price,
        "paid_amount": contract.paid_amount,
        "remaining_amount": round(contract.final_price - contract.paid_amount, 0),
        "payment_status": contract.payment_status,
        "prorated_value": contract.prorated_value,
        "freeze_days_used": contract.freeze_days_used,
        "installments": [
            {
                "sequence": i.sequence,
                "amount": i.amount,
                "paid_amount": i.paid_amount,
                "due_date": i.due_date,
                "status": i.status,
                "method": i.method,
                "note": i.note,
            }
            for i in installments
        ],
    }


# ==========================================================================
# BẢO LƯU
# ==========================================================================
@router.post("/freeze/request")
def request_freeze(
    data: FreezeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hội viên gửi yêu cầu bảo lưu thẻ."""
    member = _member(current_user, db)
    contract = _active_contract(member, db)
    if not contract:
        raise HTTPException(status_code=400, detail="Bạn chưa có hợp đồng đang hiệu lực")

    plan = contract.plan
    today = date.today()

    # --- Kiểm tra quy tắc nghiệp vụ ---
    if plan and not plan.freeze_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Gói '{plan.name}' không hỗ trợ bảo lưu thẻ.",
        )

    min_duration = plan.min_duration_for_freeze if plan else 90
    if contract.duration_days < min_duration:
        raise HTTPException(
            status_code=400,
            detail=f"Chỉ áp dụng bảo lưu cho gói từ {min_duration // 30} tháng trở lên. "
                   f"Gói hiện tại của bạn là {contract.duration_days} ngày.",
        )

    if contract.status == ContractStatus.FROZEN:
        raise HTTPException(
            status_code=400,
            detail=f"Thẻ đang trong thời gian bảo lưu đến {member.frozen_until}.",
        )

    min_days = plan.min_freeze_days if plan else 7
    max_days = plan.max_freeze_days if plan else 60
    if not (min_days <= data.days <= max_days):
        raise HTTPException(
            status_code=400,
            detail=f"Số ngày bảo lưu phải từ {min_days} đến {max_days} ngày.",
        )

    used = _current_year_freeze_days(member.id, db)
    annual_cap = max_days
    if used + data.days > annual_cap:
        raise HTTPException(
            status_code=400,
            detail=f"Bạn đã bảo lưu {used}/{annual_cap} ngày trong năm nay. "
                   f"Chỉ còn có thể bảo lưu thêm {max(0, annual_cap - used)} ngày.",
        )

    if contract.days_remaining <= data.days:
        raise HTTPException(
            status_code=400,
            detail=f"Thẻ chỉ còn {contract.days_remaining} ngày, không thể bảo lưu "
                   f"{data.days} ngày.",
        )

    start = data.start_date or today
    end = start + timedelta(days=data.days)

    req = FreezeRequest(
        member_id=member.id,
        contract_id=contract.id,
        start_date=start,
        end_date=end,
        days=data.days,
        reason=data.reason,
        status="pending",
        old_end_date=contract.end_date,
        new_end_date=contract.end_date + timedelta(days=data.days),
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return {
        "message": (
            f"Đã gửi yêu cầu bảo lưu {data.days} ngày (từ {start} đến {end}). "
            f"Vui lòng chờ lễ tân xác nhận."
        ),
        "request_id": req.id,
        "days": data.days,
        "projected_new_end_date": req.new_end_date,
        "freeze_days_used_this_year": used,
        "freeze_days_remaining": max(0, annual_cap - used - data.days),
    }


@router.post("/freeze/{request_id}/approve")
def approve_freeze(
    request_id: int,
    data: FreezeApproval,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Lễ tân/Admin duyệt yêu cầu bảo lưu và cộng bù ngày vào hạn thẻ."""
    req = db.query(FreezeRequest).filter(FreezeRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu bảo lưu")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Yêu cầu đã ở trạng thái '{req.status}'")

    contract = db.query(MembershipContract).filter(
        MembershipContract.id == req.contract_id
    ).first()
    member = db.query(Member).filter(Member.id == req.member_id).first()
    if not contract or not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hợp đồng hoặc hội viên")

    req.approved_by = current_user.full_name or current_user.username
    req.processed_at = now_local()

    if not data.approved:
        req.status = "rejected"
        if data.note:
            req.reason = f"{req.reason or ''}\n[Từ chối]: {data.note}".strip()
        db.commit()
        return {"message": "Đã từ chối yêu cầu bảo lưu", "status": req.status}

    # --- Áp dụng bảo lưu ---
    old_end = contract.end_date
    contract.end_date = old_end + timedelta(days=req.days)
    contract.freeze_days_used = (contract.freeze_days_used or 0) + req.days
    contract.status = ContractStatus.FROZEN

    member.frozen_until = req.end_date
    member.status = "frozen"
    member.expire_date = contract.end_date

    req.status = "approved"
    req.old_end_date = old_end
    req.new_end_date = contract.end_date

    db.commit()
    return {
        "message": (
            f"Đã duyệt bảo lưu {req.days} ngày cho {member.full_name}. "
            f"Hạn thẻ được cộng bù từ {old_end} thành {contract.end_date}."
        ),
        "status": req.status,
        "old_end_date": old_end,
        "new_end_date": contract.end_date,
        "freeze_days_used": contract.freeze_days_used,
    }


@router.post("/freeze/unfreeze")
def unfreeze(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Mở khóa thẻ trước thời hạn bảo lưu — hoàn lại số ngày chưa dùng."""
    member = _member(current_user, db)
    contract = _active_contract(member, db)
    today = date.today()

    if not member.frozen_until or member.frozen_until < today:
        raise HTTPException(status_code=400, detail="Thẻ hiện không trong trạng thái bảo lưu")

    unused_days = (member.frozen_until - today).days

    if contract:
        contract.end_date = contract.end_date - timedelta(days=unused_days)
        contract.freeze_days_used = max(0, (contract.freeze_days_used or 0) - unused_days)
        contract.status = ContractStatus.ACTIVE

    member.frozen_until = None
    member.status = "active"
    if contract:
        member.expire_date = contract.end_date

    db.commit()
    return {
        "message": (
            f"Đã mở khóa thẻ sớm {unused_days} ngày. "
            f"Hạn thẻ mới: {member.expire_date}."
        ),
        "unused_days_refunded": unused_days,
        "expire_date": member.expire_date,
    }


@router.get("/freeze/my")
def my_freeze_requests(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Lịch sử bảo lưu của hội viên."""
    member = _member(current_user, db)
    items = (
        db.query(FreezeRequest)
        .filter(FreezeRequest.member_id == member.id)
        .order_by(FreezeRequest.created_at.desc())
        .all()
    )
    return [
        {
            "id": f.id,
            "start_date": f.start_date,
            "end_date": f.end_date,
            "days": f.days,
            "status": f.status,
            "reason": f.reason,
            "old_end_date": f.old_end_date,
            "new_end_date": f.new_end_date,
        }
        for f in items
    ]


# ==========================================================================
# CHUYỂN NHƯỢNG
# ==========================================================================
@router.post("/transfer/request")
def request_transfer(
    data: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hội viên gửi yêu cầu chuyển nhượng gói tập."""
    member = _member(current_user, db)
    contract = _active_contract(member, db)
    if not contract:
        raise HTTPException(status_code=400, detail="Bạn chưa có hợp đồng đang hiệu lực")

    plan = contract.plan
    if plan and not plan.transfer_allowed:
        raise HTTPException(
            status_code=400, detail=f"Gói '{plan.name}' không hỗ trợ chuyển nhượng."
        )

    min_days = plan.min_days_for_transfer if plan else 30
    if contract.days_remaining < min_days:
        raise HTTPException(
            status_code=400,
            detail=f"Gói tập phải còn ít nhất {min_days} ngày mới được chuyển nhượng. "
                   f"Gói của bạn còn {contract.days_remaining} ngày.",
        )

    if contract.status == ContractStatus.FROZEN:
        raise HTTPException(status_code=400, detail="Không thể chuyển nhượng thẻ đang bảo lưu")

    # Không cho chuyển cho chính mình
    if data.to_phone.strip() == (member.phone or ""):
        raise HTTPException(status_code=400, detail="Không thể chuyển nhượng cho chính mình")

    pending = (
        db.query(TransferRequest)
        .filter(
            TransferRequest.from_contract_id == contract.id,
            TransferRequest.status == "pending",
        )
        .first()
    )
    if pending:
        raise HTTPException(
            status_code=400, detail="Đã có yêu cầu chuyển nhượng đang chờ xử lý cho hợp đồng này"
        )

    fee = plan.transfer_fee if plan else 300000

    req = TransferRequest(
        from_member_id=member.id,
        from_contract_id=contract.id,
        to_full_name=data.to_full_name.strip(),
        to_phone=data.to_phone.strip(),
        to_email=data.to_email,
        transfer_fee=fee,
        remaining_days=contract.days_remaining,
        reason=data.reason,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return {
        "message": (
            f"Đã gửi yêu cầu chuyển nhượng {contract.days_remaining} ngày còn lại "
            f"cho {req.to_full_name}. Phí chuyển nhượng: {int(fee):,}đ.".replace(",", ".")
        ),
        "request_id": req.id,
        "remaining_days": req.remaining_days,
        "transfer_fee": fee,
    }


@router.post("/transfer/{request_id}/approve")
def approve_transfer(
    request_id: int,
    data: FreezeApproval,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Duyệt chuyển nhượng: vô hiệu hóa thẻ A, tạo hợp đồng kế thừa cho B."""
    req = db.query(TransferRequest).filter(TransferRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu chuyển nhượng")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Yêu cầu đã ở trạng thái '{req.status}'")

    if not data.approved:
        req.status = "rejected"
        req.approved_by = current_user.full_name or current_user.username
        req.processed_at = now_local()
        db.commit()
        return {"message": "Đã từ chối yêu cầu chuyển nhượng", "status": req.status}

    old_contract = db.query(MembershipContract).filter(
        MembershipContract.id == req.from_contract_id
    ).first()
    from_member = db.query(Member).filter(Member.id == req.from_member_id).first()
    if not old_contract or not from_member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hợp đồng nguồn")

    # --- Tìm hoặc tạo hội viên nhận ---
    to_member = db.query(Member).filter(Member.phone == req.to_phone).first()
    created_member = False
    if not to_member:
        to_member = Member(
            full_name=req.to_full_name,
            phone=req.to_phone,
            email=req.to_email,
            status="inactive",
            join_date=date.today(),
        )
        db.add(to_member)
        db.flush()
        created_member = True
    elif to_member.id == from_member.id:
        raise HTTPException(status_code=400, detail="Không thể chuyển nhượng cho chính mình")

    # --- Tạo hợp đồng kế thừa cho B ---
    new_contract = MembershipContract(
        contract_code=_generate_contract_code(db),
        member_id=to_member.id,
        plan_id=old_contract.plan_id,
        branch_id=old_contract.branch_id,
        tier=old_contract.tier,
        time_window=old_contract.time_window,
        start_date=date.today(),
        end_date=old_contract.end_date,
        duration_days=req.remaining_days,
        list_price=old_contract.final_price,
        discount_amount=0,
        final_price=req.transfer_fee,
        paid_amount=req.transfer_fee,
        payment_status=PaymentStatus.PAID,
        status=ContractStatus.ACTIVE,
        includes_locker=old_contract.includes_locker,
        includes_towel=old_contract.includes_towel,
        includes_sauna=old_contract.includes_sauna,
        guest_passes_month=old_contract.guest_passes_month,
        previous_contract_id=old_contract.id,
        sold_by=current_user.full_name or current_user.username,
        note=f"Kế thừa từ hợp đồng {old_contract.contract_code} "
             f"(chuyển nhượng từ {from_member.full_name})",
    )
    db.add(new_contract)
    db.flush()

    # Phí chuyển nhượng ghi nhận là một kỳ đã thanh toán
    db.add(Installment(
        contract_id=new_contract.id, member_id=to_member.id, sequence=1,
        amount=req.transfer_fee, due_date=date.today(),
        paid_amount=req.transfer_fee, paid_at=now_local(),
        status=PaymentStatus.PAID, method="transfer_fee",
        note="Phí chuyển nhượng",
    ))

    # --- Vô hiệu hóa thẻ của A ---
    old_contract.status = ContractStatus.TRANSFERRED
    old_contract.cancelled_at = now_local()
    old_contract.cancel_reason = (
        f"Chuyển nhượng cho {to_member.full_name} ({to_member.phone})"
    )
    from_member.status = "inactive"
    from_member.expire_date = date.today()

    _sync_member_from_contract(to_member, new_contract)
    to_member.status = "active"

    req.status = "completed"
    req.to_member_id = to_member.id
    req.new_contract_id = new_contract.id
    req.approved_by = current_user.full_name or current_user.username
    req.processed_at = now_local()

    db.commit()
    db.refresh(new_contract)

    return {
        "message": (
            f"Đã hoàn tất chuyển nhượng. {from_member.full_name} → {to_member.full_name}, "
            f"{req.remaining_days} ngày còn lại. Hợp đồng mới: {new_contract.contract_code}."
        ),
        "status": req.status,
        "new_contract_id": new_contract.id,
        "new_contract_code": new_contract.contract_code,
        "to_member_id": to_member.id,
        "to_member_created": created_member,
        "remaining_days": req.remaining_days,
        "transfer_fee": req.transfer_fee,
        "old_contract_status": old_contract.status,
    }


# ==========================================================================
# NÂNG CẤP GÓI (PRORATED BILLING)
# ==========================================================================
@router.get("/upgrade/quote")
def upgrade_quote(
    new_plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Báo giá nâng cấp: giá trị còn lại của gói cũ được khấu trừ vào gói mới."""
    member = _member(current_user, db)
    contract = _active_contract(member, db)
    if not contract:
        raise HTTPException(status_code=400, detail="Bạn chưa có hợp đồng đang hiệu lực")

    new_plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == new_plan_id, MembershipPlan.is_active == True
    ).first()
    if not new_plan:
        raise HTTPException(status_code=404, detail="Gói tập mới không tồn tại")

    if new_plan.id == contract.plan_id:
        raise HTTPException(status_code=400, detail="Bạn đang sử dụng gói này rồi")

    credit = contract.prorated_value
    amount_due = max(0.0, new_plan.price - credit)

    return {
        "current_contract": {
            "contract_code": contract.contract_code,
            "plan_name": contract.plan.name if contract.plan else None,
            "end_date": contract.end_date,
            "days_remaining": contract.days_remaining,
            "duration_days": contract.duration_days,
            "paid_amount": contract.final_price,
        },
        "new_plan": {
            "id": new_plan.id,
            "name": new_plan.name,
            "duration_days": new_plan.duration_days,
            "price": new_plan.price,
            "tier": new_plan.tier,
        },
        "prorated_credit": round(credit, 0),
        "amount_due": round(amount_due, 0),
        "explanation": (
            f"Gói hiện tại còn {contract.days_remaining}/{contract.duration_days} ngày "
            f"chưa sử dụng, tương đương giá trị {int(credit):,}đ. "
            f"Số tiền này được khấu trừ trực tiếp vào hoá đơn gói mới.".replace(",", ".")
        ),
        "savings_note": (
            f"Bạn tiết kiệm được {int(credit):,}đ so với việc mua gói mới hoàn toàn."
            .replace(",", ".")
        ),
    }


@router.post("/upgrade")
def request_upgrade(
    data: UpgradeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nâng cấp gói: khấu trừ prorated và tạo hợp đồng mới."""
    member = _member(current_user, db)
    contract = _active_contract(member, db)
    if not contract:
        raise HTTPException(status_code=400, detail="Bạn chưa có hợp đồng đang hiệu lực")

    new_plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == data.new_plan_id, MembershipPlan.is_active == True
    ).first()
    if not new_plan:
        raise HTTPException(status_code=404, detail="Gói tập mới không tồn tại")

    if new_plan.duration_days <= contract.duration_days and new_plan.price <= contract.list_price:
        raise HTTPException(
            status_code=400,
            detail="Gói mới không cao cấp hơn gói hiện tại. Vui lòng chọn gói dài hạn "
                   "hoặc hạng thẻ cao hơn.",
        )

    credit = contract.prorated_value
    amount_due = max(0.0, new_plan.price - credit)
    today = date.today()

    # Vô hiệu hóa hợp đồng cũ
    contract.status = ContractStatus.CANCELLED
    contract.cancelled_at = now_local()
    contract.cancel_reason = f"Nâng cấp lên gói {new_plan.name}"

    # Tạo hợp đồng mới
    new_contract = MembershipContract(
        contract_code=_generate_contract_code(db),
        member_id=member.id,
        plan_id=new_plan.id,
        branch_id=contract.branch_id,
        tier=new_plan.tier,
        time_window=new_plan.time_window,
        start_date=today,
        end_date=today + timedelta(days=new_plan.duration_days),
        duration_days=new_plan.duration_days,
        list_price=new_plan.price,
        discount_amount=0,
        prorated_credit=round(credit, 0),
        final_price=amount_due,
        paid_amount=amount_due,
        payment_status=PaymentStatus.PAID,
        status=ContractStatus.ACTIVE,
        is_renewal=True,
        previous_contract_id=contract.id,
        upgraded_from_plan_id=contract.plan_id,
        sold_by=current_user.full_name or current_user.username,
        note=f"Nâng cấp từ {contract.contract_code} (khấu trừ {int(credit):,}đ)".replace(",", "."),
    )
    _apply_tier_benefits(new_contract, new_plan, new_plan.tier)
    db.add(new_contract)
    db.flush()

    db.add(Installment(
        contract_id=new_contract.id, member_id=member.id, sequence=1,
        amount=amount_due, due_date=today,
        paid_amount=amount_due, paid_at=now_local(),
        status=PaymentStatus.PAID, method=data.payment_method,
        note=f"Nâng cấp gói (đã khấu trừ {int(credit):,}đ)".replace(",", "."),
    ))

    record = UpgradeRequest(
        member_id=member.id,
        old_contract_id=contract.id,
        new_plan_id=new_plan.id,
        old_prorated_value=round(credit, 0),
        new_plan_price=new_plan.price,
        amount_due=amount_due,
        status="completed",
        new_contract_id=new_contract.id,
        approved_by=current_user.full_name or current_user.username,
        processed_at=now_local(),
    )
    db.add(record)

    _sync_member_from_contract(member, new_contract)
    member.status = "active"

    db.commit()
    db.refresh(new_contract)

    return {
        "message": (
            f"Nâng cấp thành công lên '{new_plan.name}'! Đã khấu trừ "
            f"{int(credit):,}đ từ gói cũ, bạn chỉ cần thanh toán {int(amount_due):,}đ. "
            f"Hạn thẻ mới: {new_contract.end_date}.".replace(",", ".")
        ),
        "new_contract_id": new_contract.id,
        "new_contract_code": new_contract.contract_code,
        "prorated_credit": round(credit, 0),
        "amount_due": round(amount_due, 0),
        "new_end_date": new_contract.end_date,
    }


# ==========================================================================
# CÔNG NỢ / TRẢ GÓP
# ==========================================================================
@router.get("/installments/my")
def my_installments(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Lịch trả góp và công nợ của hội viên."""
    member = _member(current_user, db)
    overdue = _sync_debt_block(member, db)
    db.commit()

    items = (
        db.query(Installment)
        .filter(Installment.member_id == member.id)
        .order_by(Installment.due_date.asc())
        .all()
    )
    today = date.today()

    return {
        "outstanding_debt": member.outstanding_debt,
        "overdue_amount": overdue,
        "is_blocked": member.is_debt_blocked,
        "block_warning": (
            "⚠️ Thẻ của bạn đang bị tạm khóa do còn công nợ quá hạn. "
            "Vui lòng thanh toán để tiếp tục sử dụng dịch vụ."
            if member.is_debt_blocked else None
        ),
        "installments": [
            {
                "id": i.id,
                "sequence": i.sequence,
                "amount": i.amount,
                "paid_amount": i.paid_amount,
                "remaining": round(i.amount - i.paid_amount, 0),
                "due_date": i.due_date,
                "status": i.status,
                "days_overdue": max(0, (today - i.due_date).days)
                if i.status != PaymentStatus.PAID else 0,
                "note": i.note,
            }
            for i in items
        ],
    }


@router.post("/installments/{installment_id}/pay")
def pay_installment(
    installment_id: int,
    data: InstallmentPay,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Ghi nhận thanh toán một kỳ (lễ tân thu tiền)."""
    inst = db.query(Installment).filter(Installment.id == installment_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Không tìm thấy kỳ thanh toán")

    remaining = inst.amount - (inst.paid_amount or 0)
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Kỳ này đã được thanh toán đủ")

    pay = min(data.amount, remaining)
    inst.paid_amount = round((inst.paid_amount or 0) + pay, 0)
    inst.method = data.method
    if data.note:
        inst.note = f"{inst.note or ''}\n[Thu tiền]: {data.note}".strip()

    if inst.paid_amount >= inst.amount:
        inst.status = PaymentStatus.PAID
        inst.paid_at = now_local()

    contract = db.query(MembershipContract).filter(
        MembershipContract.id == inst.contract_id
    ).first()
    if contract:
        _recalc_installments_status(contract, db)

    member = db.query(Member).filter(Member.id == inst.member_id).first()
    if member:
        overdue = _sync_debt_block(member, db)
        # Tự mở khóa thẻ nếu đã hết nợ quá hạn
        if not member.is_debt_blocked and member.status == "active":
            member.is_debt_blocked = False
    else:
        overdue = 0.0

    db.commit()

    return {
        "message": (
            f"Đã thu {int(pay):,}đ cho kỳ {inst.sequence}. "
            f"Còn lại {int(max(0, inst.amount - inst.paid_amount)):,}đ.".replace(",", ".")
        ),
        "installment_id": inst.id,
        "paid_amount": inst.paid_amount,
        "status": inst.status,
        "overdue_remaining": overdue,
        "member_unblocked": bool(member and not member.is_debt_blocked),
    }


@router.get("/debt/overdue")
def list_overdue_debt(
    current_user: User = Depends(require_operations), db: Session = Depends(get_db)
):
    """Danh sách hội viên đang có công nợ quá hạn (báo cáo cho lễ tân)."""
    today = date.today()
    rows = (
        db.query(
            Member.id,
            Member.full_name,
            Member.phone,
            func.sum(Installment.amount - Installment.paid_amount).label("overdue"),
            func.min(Installment.due_date).label("oldest_due"),
        )
        .join(Installment, Installment.member_id == Member.id)
        .filter(
            Installment.due_date < today,
            Installment.status != PaymentStatus.PAID,
        )
        .group_by(Member.id, Member.full_name, Member.phone)
        .order_by(func.sum(Installment.amount - Installment.paid_amount).desc())
        .all()
    )

    return {
        "total_members": len(rows),
        "total_overdue": round(sum(float(r.overdue or 0) for r in rows), 0),
        "members": [
            {
                "member_id": r.id,
                "full_name": r.full_name,
                "phone": r.phone,
                "overdue_amount": round(float(r.overdue or 0), 0),
                "oldest_due_date": r.oldest_due,
                "days_overdue": (today - r.oldest_due).days if r.oldest_due else 0,
            }
            for r in rows
        ],
    }


# ==========================================================================
# LEADS & TẬP THỬ (CRM)
# ==========================================================================
@router.post("/trial/register")
def register_trial(data: TrialPassRequest, db: Session = Depends(get_db)):
    """Khách vãng lai đăng ký tập thử — sinh QR và OTP chống lạm dụng."""
    phone = data.phone.strip()

    # Chống 1 người đăng ký nhiều lần
    existing_member = db.query(Member).filter(Member.phone == phone).first()
    if existing_member and existing_member.expire_date and existing_member.expire_date >= date.today():
        raise HTTPException(
            status_code=400,
            detail="Số điện thoại này đã có thẻ hội viên đang hiệu lực. "
                   "Ưu đãi tập thử chỉ dành cho khách hàng mới.",
        )

    prior = (
        db.query(TrialPass)
        .filter(TrialPass.phone == phone)
        .order_by(TrialPass.created_at.desc())
        .first()
    )
    if prior:
        raise HTTPException(
            status_code=400,
            detail="Số điện thoại này đã từng đăng ký tập thử. "
                   "Mỗi khách hàng chỉ được dùng ưu đãi tập thử một lần.",
        )

    today = date.today()
    otp = f"{random.randint(100000, 999999)}"
    qr = f"TRIAL-{secrets.token_hex(4).upper()}"

    trial = TrialPass(
        full_name=data.full_name.strip(),
        phone=phone,
        branch_id=data.branch_id,
        qr_code=qr,
        days=data.days,
        start_date=today,
        end_date=today + timedelta(days=data.days),
        otp_code=otp,
        otp_verified=False,
        otp_expires_at=now_local() + timedelta(minutes=10),
        status="pending",
    )
    db.add(trial)
    db.flush()

    lead = Lead(
        full_name=trial.full_name,
        phone=phone,
        source="website",
        branch_id=data.branch_id,
        stage=LeadStage.NEW,
        trial_pass_id=trial.id,
    )
    db.add(lead)
    db.commit()
    db.refresh(trial)

    return {
        "message": (
            f"Đã tạo vé tập thử {data.days} ngày cho {trial.full_name}. "
            f"Mã OTP đã được gửi tới số {phone}."
        ),
        "trial_pass_id": trial.id,
        "qr_code": qr,
        "start_date": trial.start_date,
        "end_date": trial.end_date,
        "days": trial.days,
        "otp_required": True,
        "debug_otp": otp,
        "otp_note": (
            "Trong môi trường demo, mã OTP được trả về ở trường 'debug_otp'. "
            "Khi triển khai thật, mã này chỉ được gửi qua SMS/Zalo."
        ),
    }


@router.post("/trial/verify-otp")
def verify_trial_otp(data: OTPVerify, db: Session = Depends(get_db)):
    """Xác thực OTP để kích hoạt vé tập thử."""
    trial = (
        db.query(TrialPass)
        .filter(TrialPass.phone == data.phone.strip())
        .order_by(TrialPass.created_at.desc())
        .first()
    )
    if not trial:
        raise HTTPException(status_code=404, detail="Không tìm thấy vé tập thử cho số này")
    if trial.otp_verified:
        raise HTTPException(status_code=400, detail="Vé tập thử này đã được xác thực rồi")

    if trial.otp_attempts >= 5:
        raise HTTPException(
            status_code=429, detail="Bạn đã nhập sai quá 5 lần. Vui lòng liên hệ hotline."
        )

    if trial.otp_expires_at and trial.otp_expires_at < now_local():
        raise HTTPException(
            status_code=400, detail="Mã OTP đã hết hạn. Vui lòng đăng ký lại."
        )

    if trial.otp_code != data.otp_code.strip():
        trial.otp_attempts = (trial.otp_attempts or 0) + 1
        db.commit()
        remaining = max(0, 5 - trial.otp_attempts)
        raise HTTPException(
            status_code=400,
            detail=f"Mã OTP không đúng. Bạn còn {remaining} lần thử.",
        )

    trial.otp_verified = True
    trial.status = "active"
    db.commit()

    return {
        "message": (
            f"Xác thực thành công! Vé tập thử {trial.days} ngày của bạn đã kích hoạt, "
            f"có hiệu lực đến {trial.end_date}."
        ),
        "qr_code": trial.qr_code,
        "end_date": trial.end_date,
        "visits_used": trial.visits_used,
        "note": (
            "Đưa mã QR này cho lễ tân khi đến tập. Vé bao gồm toàn bộ khu tạ, "
            "máy cardio và các lớp tập nhóm."
        ),
    }


@router.get("/leads")
def list_leads(
    stage: Optional[str] = None,
    assigned_to: Optional[str] = None,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Danh sách khách tập thử theo pipeline CRM."""
    query = db.query(Lead)
    if stage:
        query = query.filter(Lead.stage == stage)
    if assigned_to:
        query = query.filter(Lead.assigned_to == assigned_to)
    leads = query.order_by(Lead.created_at.desc()).limit(200).all()

    # Thống kê pipeline
    stage_counts = dict(
        db.query(Lead.stage, func.count(Lead.id)).group_by(Lead.stage).all()
    )

    return {
        "total": len(leads),
        "pipeline": {
            s: stage_counts.get(s, 0)
            for s in LeadStage.ALL
        },
        "conversion_rate": round(
            stage_counts.get(LeadStage.WON, 0) / len(leads) * 100, 1
        ) if leads else 0.0,
        "leads": [
            {
                "id": l.id,
                "full_name": l.full_name,
                "phone": l.phone,
                "email": l.email,
                "source": l.source,
                "stage": l.stage,
                "assigned_to": l.assigned_to,
                "trial_pass_id": l.trial_pass_id,
                "first_visit_at": l.first_visit_at,
                "inbody_done_at": l.inbody_done_at,
                "consultation_note": l.consultation_note,
                "lost_reason": l.lost_reason,
                "created_at": l.created_at,
                "days_since_created": (date.today() - l.created_at.date()).days
                if l.created_at else 0,
            }
            for l in leads
        ],
    }


@router.put("/leads/{lead_id}")
def update_lead(
    lead_id: int,
    data: LeadUpdate,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Cập nhật tiến trình chăm sóc khách tập thử."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách hàng")

    if data.stage:
        if data.stage not in LeadStage.ALL:
            raise HTTPException(
                status_code=422,
                detail=f"Trạng thái không hợp lệ. Chọn một trong: {', '.join(LeadStage.ALL)}",
            )
        # Ghi nhận mốc thời gian theo trạng thái
        if data.stage == LeadStage.FIRST_VISIT and not lead.first_visit_at:
            lead.first_visit_at = now_local()
        if data.stage == LeadStage.INBODY_CONSULTED and not lead.inbody_done_at:
            lead.inbody_done_at = now_local()
        lead.stage = data.stage

    for field in ("assigned_to", "consultation_note", "lost_reason", "interested_plan_id"):
        value = getattr(data, field)
        if value is not None:
            setattr(lead, field, value)

    lead.updated_at = now_local()
    db.commit()

    return {
        "message": f"Đã cập nhật khách hàng {lead.full_name} sang trạng thái '{lead.stage}'",
        "lead_id": lead.id,
        "stage": lead.stage,
    }


@router.post("/leads/{lead_id}/convert")
def convert_lead(
    lead_id: int,
    plan_id: int,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Chốt gói thành công: tạo hội viên + hợp đồng từ lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách hàng")
    if lead.stage == LeadStage.WON:
        raise HTTPException(status_code=400, detail="Khách hàng này đã được chốt gói rồi")

    plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == plan_id, MembershipPlan.is_active == True
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Gói tập không tồn tại")

    # Tạo hoặc tái sử dụng hồ sơ hội viên
    member = db.query(Member).filter(Member.phone == lead.phone).first()
    if not member:
        member = Member(
            full_name=lead.full_name,
            phone=lead.phone,
            email=lead.email,
            status="active",
            join_date=date.today(),
        )
        db.add(member)
        db.flush()

    today = date.today()
    contract = MembershipContract(
        contract_code=_generate_contract_code(db),
        member_id=member.id,
        plan_id=plan.id,
        branch_id=lead.branch_id,
        tier=plan.tier,
        time_window=plan.time_window,
        start_date=today,
        end_date=today + timedelta(days=plan.duration_days),
        duration_days=plan.duration_days,
        list_price=plan.price,
        final_price=plan.price,
        paid_amount=plan.price,
        payment_status=PaymentStatus.PAID,
        status=ContractStatus.ACTIVE,
        sold_by=lead.assigned_to or current_user.full_name or current_user.username,
        note=f"Chốt từ khách tập thử (lead #{lead.id})",
    )
    _apply_tier_benefits(contract, plan, plan.tier)
    db.add(contract)
    db.flush()

    db.add(Installment(
        contract_id=contract.id, member_id=member.id, sequence=1,
        amount=plan.price, due_date=today,
        paid_amount=plan.price, paid_at=now_local(),
        status=PaymentStatus.PAID, method="cash",
        note="Chốt gói từ tập thử",
    ))

    _sync_member_from_contract(member, contract)
    member.status = "active"

    lead.stage = LeadStage.WON
    lead.converted_member_id = member.id
    lead.converted_contract_id = contract.id
    lead.updated_at = now_local()

    db.commit()
    db.refresh(contract)

    return {
        "message": (
            f"🎉 Chốt gói thành công! {lead.full_name} đã trở thành hội viên với gói "
            f"'{plan.name}'. Hợp đồng: {contract.contract_code}."
        ),
        "member_id": member.id,
        "contract_id": contract.id,
        "contract_code": contract.contract_code,
        "end_date": contract.end_date,
        "lead_stage": lead.stage,
    }


# ==========================================================================
# VÍ TRẢ TRƯỚC
# ==========================================================================
@router.get("/wallet/my")
def my_wallet(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Số dư ví và lịch sử giao dịch."""
    member = _member(current_user, db)
    wallet = _wallet_for(member, db)
    txns = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.member_id == member.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "balance": wallet.balance,
        "total_topup": wallet.total_topup,
        "total_spent": wallet.total_spent,
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "kind": t.kind,
                "reference": t.reference,
                "note": t.note,
                "created_at": t.created_at,
            }
            for t in txns
        ],
    }


@router.post("/wallet/{member_id}/topup")
def wallet_topup_for_member(
    member_id: int,
    data: WalletTopup,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Nạp tiền vào ví của một hội viên (lễ tân thu tiền mặt/chuyển khoản)."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")

    wallet = _wallet_for(member, db)
    wallet.balance = round((wallet.balance or 0) + data.amount, 0)
    wallet.total_topup = round((wallet.total_topup or 0) + data.amount, 0)

    txn = WalletTransaction(
        wallet_id=wallet.id,
        member_id=member.id,
        amount=data.amount,
        balance_after=wallet.balance,
        kind="topup",
        reference=f"TOPUP-{secrets.token_hex(3).upper()}",
        note=data.note or f"Nạp ví qua {data.method}",
    )
    db.add(txn)
    db.commit()

    return {
        "message": (
            f"Đã nạp {int(data.amount):,}đ vào ví của {member.full_name}. "
            f"Số dư mới: {int(wallet.balance):,}đ.".replace(",", ".")
        ),
        "balance": wallet.balance,
        "transaction_id": txn.id,
    }