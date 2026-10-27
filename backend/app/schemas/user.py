from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    email: Optional[str] = None
    phone: Optional[str] = None

class FreezeRequest(BaseModel):
    days: int = Field(default=14, ge=1, le=60, description="Số ngày bảo lưu (1 - 60 ngày)")
