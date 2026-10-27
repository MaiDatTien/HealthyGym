from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.listing import MembershipPlan, GymClass

router = APIRouter(prefix="/recommendations", tags=["AI Recommendations"])

@router.get("/")
def get_recommendations(goal: str = "giam-can", db: Session = Depends(get_db)):
    plans = db.query(MembershipPlan).filter(MembershipPlan.is_popular == True, MembershipPlan.is_active == True).all()
    if goal == "tang-co":
        classes = db.query(GymClass).filter(GymClass.category.in_(["Strength", "Boxing"])).all()
    else:
        classes = db.query(GymClass).filter(GymClass.category.in_(["Yoga", "HIIT"])).all()
    return {
        "goal": goal,
        "recommended_plans": plans,
        "recommended_classes": classes
    }
