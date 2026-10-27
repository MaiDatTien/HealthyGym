from pydantic import BaseModel, Field
from typing import Optional

class MembershipPlanBase(BaseModel):
    name: str
    duration_days: int = Field(..., gt=0)
    price: float = Field(..., ge=0)
    benefits: Optional[str] = None
    includes_pt: bool = False
    is_popular: bool = False

class BookingCreate(BaseModel):
    gym_class_id: int
    note: Optional[str] = None

class OrderCreate(BaseModel):
    plan_id: int
    voucher_code: Optional[str] = None
    payment_method: str = "Chuyển khoản QR"

class FeedbackCreate(BaseModel):
    rating: int = Field(default=5, ge=1, le=5)
    comment: str = Field(..., min_length=5)
