from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.listing import MembershipPlan, GymClass, Branch
from app.models.user import Trainer

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/")
def search_gym(q: str = Query("", description="Từ khóa tìm kiếm"), db: Session = Depends(get_db)):
    keyword = f"%{q}%"
    plans = db.query(MembershipPlan).filter(MembershipPlan.name.ilike(keyword), MembershipPlan.is_active == True).all()
    classes = db.query(GymClass).filter(GymClass.name.ilike(keyword) | GymClass.category.ilike(keyword)).all()
    trainers = db.query(Trainer).filter(Trainer.full_name.ilike(keyword) | Trainer.specialty.ilike(keyword)).all()
    branches = db.query(Branch).filter(Branch.name.ilike(keyword) | Branch.address.ilike(keyword)).all()
    return {
        "query": q,
        "plans": plans,
        "classes": classes,
        "trainers": trainers,
        "branches": branches
    }
