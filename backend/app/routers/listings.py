from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.listing import MembershipPlan, GymClass, Branch, Facility, Article
from app.models.interaction import Booking
from app.models.user import Trainer

router = APIRouter(prefix="/listings", tags=["Listings - HealthyGym"])

@router.get("/plans")
def get_plans(db: Session = Depends(get_db)):
    return db.query(MembershipPlan).filter(MembershipPlan.is_active == True).order_by(MembershipPlan.price.asc()).all()

@router.get("/classes")
def get_classes(db: Session = Depends(get_db)):
    classes = db.query(GymClass).all()
    result = []
    for c in classes:
        enrolled = db.query(func.count(Booking.id)).filter(
            Booking.gym_class_id == c.id,
            Booking.status == "confirmed"
        ).scalar() or 0
        result.append({
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "schedule_time": c.schedule_time,
            "room": c.room,
            "capacity": c.capacity,
            "enrolled_count": enrolled,
            "available_spots": max(0, c.capacity - enrolled),
            "trainer_name": c.trainer.full_name if c.trainer else "HLV HealthyGym",
            "branch_name": c.branch.name if c.branch else "Cơ sở chính",
            "description": c.description
        })
    return result

@router.get("/trainers")
def get_trainers(db: Session = Depends(get_db)):
    return db.query(Trainer).all()

@router.get("/branches")
def get_branches(db: Session = Depends(get_db)):
    return db.query(Branch).filter(Branch.is_active == True).all()

@router.get("/facilities")
def get_facilities(db: Session = Depends(get_db)):
    return db.query(Facility).all()

@router.get("/articles")
def get_articles(db: Session = Depends(get_db)):
    return db.query(Article).filter(Article.is_published == True).order_by(Article.created_at.desc()).all()
