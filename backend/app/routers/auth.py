from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app.models.user import User, Member
from app.schemas.user import UserLogin, UserRegister
from app.security import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

def sync_member_status(member: Member, db: Session):
    if not member:
        return
    today = date.today()
    changed = False
    if member.frozen_until and member.frozen_until >= today:
        if member.status != "frozen":
            member.status = "frozen"
            changed = True
    elif member.expire_date:
        if member.expire_date < today and member.status != "expired":
            member.status = "expired"
            changed = True
        elif member.expire_date >= today and member.status != "active":
            member.status = "active"
            changed = True
    if changed:
        db.commit()
        db.refresh(member)

@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu")
    token = create_access_token({"sub": user.username, "role": user.role})
    member = db.query(Member).filter(Member.user_id == user.id).first()
    sync_member_status(member, db)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "member_id": member.id if member else None,
            "member_status": member.status if member else None,
            "plan_name": member.current_plan.name if (member and member.current_plan) else "Chưa đăng ký gói",
            "expire_date": str(member.expire_date) if member and member.expire_date else None,
            "frozen_until": str(member.frozen_until) if member and member.frozen_until else None,
        }
    }

@router.post("/register")
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")
    if data.email and db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email này đã được sử dụng")

    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        role="member"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Nghiệp vụ chuẩn: Tài khoản mới tạo ở trạng thái 'inactive' (chưa có gói tập), cần mua gói để kích hoạt
    member = Member(
        user_id=user.id,
        full_name=data.full_name,
        phone=data.phone,
        email=data.email,
        status="inactive",
        join_date=date.today(),
        expire_date=None
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    token = create_access_token({"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "member_id": member.id,
            "member_status": member.status,
            "plan_name": "Chưa đăng ký gói",
            "expire_date": None,
            "frozen_until": None
        }
    }

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    sync_member_status(member, db)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role,
        "member_id": member.id if member else None,
        "member_status": member.status if member else None,
        "plan_name": member.current_plan.name if (member and member.current_plan) else "Chưa đăng ký gói",
        "expire_date": str(member.expire_date) if member and member.expire_date else None,
        "frozen_until": str(member.frozen_until) if member and member.frozen_until else None,
    }
