from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User, Member, Trainer
from app.models.listing import MembershipPlan, GymClass, Branch, Facility
from app.models.interaction import Order, Booking, CheckInLog
from app.schemas.listing import MembershipPlanBase
from app.security import require_admin, require_staff_or_admin

router = APIRouter(prefix="/admin", tags=["Admin Full CRUD & Reports"])

class ClassInput(BaseModel):
    name: str
    category: str = "Yoga"
    schedule_time: str
    room: str = "Studio A"
    capacity: int = 20
    trainer_id: Optional[int] = None
    branch_id: Optional[int] = None
    description: Optional[str] = None

class TrainerInput(BaseModel):
    full_name: str
    specialty: str
    phone: Optional[str] = None
    experience_years: int = 3
    bio: Optional[str] = None
    branch_id: Optional[int] = None

class BranchInput(BaseModel):
    name: str
    address: str
    phone: Optional[str] = "1900 6868"
    opening_hours: str = "05:30 - 22:30"

class FacilityInput(BaseModel):
    name: str
    category: str = "Cardio"
    quantity: int = 10
    status: str = "Hoạt động tốt"
    description: Optional[str] = None

class MemberUpdateInput(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    status: str = "active"
    expire_date: Optional[date] = None
    current_plan_id: Optional[int] = None

@router.get("/reports")
def get_admin_reports(db: Session = Depends(get_db)):
    total_members = db.query(func.count(Member.id)).scalar() or 0
    active_members = db.query(func.count(Member.id)).filter(Member.status == "active").scalar() or 0
    total_revenue = db.query(func.sum(Order.total_amount)).filter(Order.status == "completed").scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_bookings = db.query(func.count(Booking.id)).filter(Booking.status == "confirmed").scalar() or 0
    total_trainers = db.query(func.count(Trainer.id)).scalar() or 0
    total_checkins = db.query(func.count(CheckInLog.id)).scalar() or 0
    return {
        "total_members": total_members,
        "active_members": active_members,
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_bookings": total_bookings,
        "total_trainers": total_trainers,
        "total_checkins": total_checkins,
    }

# --- CRUD GÓI TẬP (PLANS) ---
@router.post("/plans")
def create_plan(data: MembershipPlanBase, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    plan = MembershipPlan(**data.model_dump(), is_active=True)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@router.put("/plans/{plan_id}")
def update_plan(plan_id: int, data: MembershipPlanBase, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy gói tập")
    for k, v in data.model_dump().items():
        setattr(plan, k, v)
    db.commit()
    db.refresh(plan)
    return plan

@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy gói tập")
    db.delete(plan)
    db.commit()
    return {"message": "Đã xóa gói tập thành công"}

# --- CRUD LỚP HỌC (CLASSES) ---
@router.post("/classes")
def create_class(data: ClassInput, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = GymClass(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put("/classes/{class_id}")
def update_class(class_id: int, data: ClassInput, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = db.query(GymClass).filter(GymClass.id == class_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/classes/{class_id}")
def delete_class(class_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = db.query(GymClass).filter(GymClass.id == class_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")
    db.delete(obj)
    db.commit()
    return {"message": "Đã xóa lớp học thành công"}

# --- CRUD HUẤN LUYỆN VIÊN (TRAINERS) ---
@router.post("/trainers")
def create_trainer(data: TrainerInput, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = Trainer(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put("/trainers/{trainer_id}")
def update_trainer(trainer_id: int, data: TrainerInput, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = db.query(Trainer).filter(Trainer.id == trainer_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy HLV")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/trainers/{trainer_id}")
def delete_trainer(trainer_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = db.query(Trainer).filter(Trainer.id == trainer_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy HLV")
    db.delete(obj)
    db.commit()
    return {"message": "Đã xóa HLV thành công"}

# --- CRUD CHI NHÁNH (BRANCHES) ---
@router.post("/branches")
def create_branch(data: BranchInput, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = Branch(**data.model_dump(), is_active=True)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put("/branches/{branch_id}")
def update_branch(branch_id: int, data: BranchInput, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = db.query(Branch).filter(Branch.id == branch_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy chi nhánh")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/branches/{branch_id}")
def delete_branch(branch_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = db.query(Branch).filter(Branch.id == branch_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy chi nhánh")
    db.delete(obj)
    db.commit()
    return {"message": "Đã xóa chi nhánh thành công"}

# --- CRUD CƠ SỞ VẬT CHẤT (FACILITIES) ---
@router.post("/facilities")
def create_facility(data: FacilityInput, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = Facility(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put("/facilities/{facility_id}")
def update_facility(facility_id: int, data: FacilityInput, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = db.query(Facility).filter(Facility.id == facility_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/facilities/{facility_id}")
def delete_facility(facility_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = db.query(Facility).filter(Facility.id == facility_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    db.delete(obj)
    db.commit()
    return {"message": "Đã xóa thiết bị thành công"}

# --- CRUD HỘI VIÊN (MEMBERS) ---
@router.get("/members")
def admin_list_members(_: User = Depends(require_staff_or_admin), db: Session = Depends(get_db)):
    members = db.query(Member).order_by(Member.id.asc()).all()
    return [
        {
            "id": m.id,
            "full_name": m.full_name,
            "phone": m.phone,
            "email": m.email,
            "current_plan_id": m.current_plan_id,
            "plan_name": m.current_plan.name if m.current_plan else "Chưa có gói",
            "status": m.status,
            "expire_date": str(m.expire_date) if m.expire_date else "",
            "frozen_until": str(m.frozen_until) if m.frozen_until else None,
        }
        for m in members
    ]

@router.post("/members")
def create_member(data: MemberUpdateInput, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = Member(**data.model_dump(), join_date=date.today())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put("/members/{member_id}")
def update_member(member_id: int, data: MemberUpdateInput, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = db.query(Member).filter(Member.id == member_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/members/{member_id}")
def delete_member(member_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    obj = db.query(Member).filter(Member.id == member_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội viên")
    db.delete(obj)
    db.commit()
    return {"message": "Đã xóa hội viên thành công"}
