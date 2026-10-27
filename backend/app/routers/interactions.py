from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
from app.database import get_db
from app.models.interaction import Booking, Order, Voucher, Feedback, CheckInLog
from app.models.listing import MembershipPlan, GymClass
from app.models.user import User, Member
from app.schemas.listing import BookingCreate, OrderCreate, FeedbackCreate
from app.schemas.user import FreezeRequest
from app.security import get_current_user, require_staff_or_admin

router = APIRouter(prefix="/interactions", tags=["Interactions - Nghiệp vụ Phòng Gym"])

class FreeTrialRequest(BaseModel):
    full_name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=8)

def get_or_create_member(user: User, db: Session) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        member = Member(
            user_id=user.id,
            full_name=user.full_name or user.username,
            email=user.email,
            status="inactive",
            join_date=date.today()
        )
        db.add(member)
        db.commit()
        db.refresh(member)
    return member

@router.post("/free-trial")
def register_free_trial(data: FreeTrialRequest, db: Session = Depends(get_db)):
    existing = db.query(Member).filter(Member.phone == data.phone.strip()).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Số điện thoại này đã từng đăng ký tại hệ thống. Ưu đãi 7 ngày miễn phí chỉ áp dụng cho khách hàng lần đầu!"
        )
    today = date.today()
    trial_member = Member(
        full_name=data.full_name.strip(),
        phone=data.phone.strip(),
        status="active",
        join_date=today,
        expire_date=today + timedelta(days=7)
    )
    db.add(trial_member)
    db.commit()
    db.refresh(trial_member)
    return {
        "message": f"Chúc mừng {trial_member.full_name}! Bạn đã nhận 7 ngày tập luyện miễn phí (Hạn trải nghiệm đến {trial_member.expire_date}).",
        "member_id": trial_member.id,
        "expire_date": str(trial_member.expire_date)
    }

@router.get("/vouchers/validate")
def validate_voucher(code: str, plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_id, MembershipPlan.is_active == True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy gói tập")
    voucher = db.query(Voucher).filter(Voucher.code == code.strip().upper(), Voucher.is_active == True).first()
    if not voucher:
        raise HTTPException(status_code=400, detail="Mã giảm giá không tồn tại hoặc đã ngừng áp dụng")
    if voucher.valid_until and voucher.valid_until < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Mã giảm giá đã hết hạn sử dụng")

    discount = min(plan.price * (voucher.discount_percent / 100.0), voucher.max_discount_amount)
    final_price = max(0, plan.price - discount)
    return {
        "code": voucher.code,
        "discount_percent": voucher.discount_percent,
        "discount_amount": discount,
        "original_price": plan.price,
        "final_price": final_price
    }

@router.post("/orders")
def checkout_plan(
    data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == data.plan_id, MembershipPlan.is_active == True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Gói tập không tồn tại hoặc đã ngừng kinh doanh")

    member = get_or_create_member(current_user, db)
    discount = 0.0
    applied_code = None

    if data.voucher_code and data.voucher_code.strip():
        code_upper = data.voucher_code.strip().upper()
        voucher = db.query(Voucher).filter(Voucher.code == code_upper, Voucher.is_active == True).first()
        if not voucher:
            raise HTTPException(status_code=400, detail=f"Mã giảm giá '{code_upper}' không hợp lệ")
        if voucher.valid_until and voucher.valid_until < datetime.utcnow():
            raise HTTPException(status_code=400, detail=f"Mã giảm giá '{code_upper}' đã hết hạn")
        discount = min(plan.price * (voucher.discount_percent / 100.0), voucher.max_discount_amount)
        applied_code = code_upper

    total = max(0.0, plan.price - discount)

    order = Order(
        member_id=member.id,
        plan_id=plan.id,
        voucher_code=applied_code,
        discount_amount=discount,
        total_amount=total,
        payment_method=data.payment_method,
        status="completed"
    )
    db.add(order)

    today = date.today()
    start_date = member.expire_date if (member.expire_date and member.expire_date > today) else today
    member.current_plan_id = plan.id
    member.expire_date = start_date + timedelta(days=plan.duration_days)
    member.frozen_until = None
    member.status = "active"

    db.commit()
    db.refresh(order)
    return {
        "message": f"Tham gia '{plan.name}' thành công! Hạn thẻ của bạn đến ngày {member.expire_date}.",
        "order_id": order.id,
        "discount_amount": discount,
        "total_amount": total,
        "new_expire_date": str(member.expire_date)
    }

@router.get("/orders/my")
def my_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = get_or_create_member(current_user, db)
    orders = db.query(Order).filter(Order.member_id == member.id).order_by(Order.created_at.desc()).all()
    return [
        {
            "id": o.id,
            "plan_name": o.plan.name if o.plan else "Gói tập",
            "voucher_code": o.voucher_code,
            "discount_amount": o.discount_amount,
            "total_amount": o.total_amount,
            "payment_method": o.payment_method,
            "status": o.status,
            "created_at": o.created_at
        }
        for o in orders
    ]

@router.post("/bookings")
def create_booking(
    data: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member = get_or_create_member(current_user, db)
    today = date.today()

    if member.frozen_until and member.frozen_until >= today:
        raise HTTPException(
            status_code=400,
            detail=f"Thẻ tập của bạn đang bảo lưu đến {member.frozen_until}. Vui lòng mở khóa thẻ trước khi đặt lịch!"
        )
    if not member.expire_date or member.expire_date < today or member.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Thẻ hội viên của bạn chưa kích hoạt hoặc đã hết hạn. Vui lòng tham gia Gói tập trước khi đặt lịch lớp học!"
        )

    gym_class = db.query(GymClass).filter(GymClass.id == data.gym_class_id).first()
    if not gym_class:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    existing = db.query(Booking).filter(
        Booking.member_id == member.id,
        Booking.gym_class_id == gym_class.id,
        Booking.status == "confirmed"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Bạn đã có lịch đặt lớp '{gym_class.name}' rồi!")

    enrolled = db.query(func.count(Booking.id)).filter(
        Booking.gym_class_id == gym_class.id,
        Booking.status == "confirmed"
    ).scalar() or 0
    if enrolled >= gym_class.capacity:
        raise HTTPException(status_code=400, detail=f"Lớp '{gym_class.name}' đã đủ {gym_class.capacity} học viên!")

    booking = Booking(
        member_id=member.id,
        gym_class_id=gym_class.id,
        note=data.note,
        status="confirmed"
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return {"message": f"Đặt lịch lớp '{gym_class.name}' thành công!", "booking_id": booking.id}

@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member = get_or_create_member(current_user, db)
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.member_id == member.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch đặt")
    booking.status = "cancelled"
    db.commit()
    return {"message": "Đã hủy lịch tập thành công"}

@router.get("/bookings/my")
def my_bookings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = get_or_create_member(current_user, db)
    items = db.query(Booking).filter(Booking.member_id == member.id).order_by(Booking.booking_date.desc()).all()
    return [
        {
            "id": b.id,
            "class_name": b.gym_class.name if b.gym_class else "Lớp Gym",
            "category": b.gym_class.category if b.gym_class else "",
            "schedule_time": b.gym_class.schedule_time if b.gym_class else "",
            "room": b.gym_class.room if b.gym_class else "",
            "status": b.status,
            "booking_date": b.booking_date
        }
        for b in items
    ]

@router.post("/freeze")
def freeze_membership(
    req: FreezeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member = get_or_create_member(current_user, db)
    today = date.today()
    if not member.expire_date or member.expire_date <= today:
        raise HTTPException(status_code=400, detail="Thẻ của bạn đã hết hạn hoặc chưa đăng ký gói tập nên không thể bảo lưu")
    if member.frozen_until and member.frozen_until >= today:
        raise HTTPException(status_code=400, detail=f"Thẻ đã đang trong thời gian bảo lưu đến {member.frozen_until}")

    member.frozen_until = today + timedelta(days=req.days)
    member.expire_date = member.expire_date + timedelta(days=req.days)
    member.status = "frozen"
    db.commit()
    return {
        "message": f"Đã bảo lưu thẻ {req.days} ngày (đến {member.frozen_until}). Hạn thẻ mới được cộng bù đến {member.expire_date}.",
        "frozen_until": str(member.frozen_until),
        "expire_date": str(member.expire_date)
    }

@router.post("/unfreeze")
def unfreeze_membership(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member = get_or_create_member(current_user, db)
    today = date.today()
    if not member.frozen_until or member.frozen_until < today:
        raise HTTPException(status_code=400, detail="Thẻ của bạn hiện không nằm trong trạng thái bảo lưu")

    unused_freeze_days = (member.frozen_until - today).days
    if member.expire_date and unused_freeze_days > 0:
        member.expire_date = member.expire_date - timedelta(days=unused_freeze_days)
    member.frozen_until = None
    member.status = "active"
    db.commit()
    return {
        "message": "Đã kích hoạt lại thẻ hội viên thành công!",
        "expire_date": str(member.expire_date)
    }

@router.post("/checkin/{member_id}")
def staff_checkin(
    member_id: int,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")
    today = date.today()
    if member.frozen_until and member.frozen_until >= today:
        raise HTTPException(status_code=400, detail=f"Không thể Check-in: Thẻ hội viên đang bảo lưu đến {member.frozen_until}")
    if not member.expire_date or member.expire_date < today:
        raise HTTPException(status_code=400, detail="Không thể Check-in: Thẻ hội viên đã hết hạn hoặc chưa mua gói tập")

    log = CheckInLog(member_id=member.id, checked_by=staff_user.username)
    db.add(log)
    db.commit()
    return {"message": f"Check-in 24/7 thành công cho hội viên {member.full_name}!"}

@router.get("/feedbacks")
def get_feedbacks(db: Session = Depends(get_db)):
    return db.query(Feedback).order_by(Feedback.created_at.desc()).all()

@router.post("/feedbacks")
def send_feedback(
    data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fb = Feedback(
        member_name=current_user.full_name or current_user.username,
        rating=data.rating,
        comment=data.comment
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb
