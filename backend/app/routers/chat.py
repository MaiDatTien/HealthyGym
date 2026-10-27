from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.chat import ChatMessage
from app.models.listing import MembershipPlan, GymClass

router = APIRouter(prefix="/chat", tags=["AI Chat Assistant"])

class ChatRequest(BaseModel):
    username: str = "Hội viên"
    message: str

@router.post("/")
def chat_with_ai(req: ChatRequest, db: Session = Depends(get_db)):
    msg_lower = req.message.lower()
    plans = db.query(MembershipPlan).filter(MembershipPlan.is_active == True).all()
    classes = db.query(GymClass).all()

    if "giá" in msg_lower or "gói" in msg_lower or "bao nhiêu" in msg_lower or "voucher" in msg_lower:
        plan_info = " | ".join([f"{p.name}: {int(p.price):,}đ ({p.duration_days} ngày)" for p in plans])
        reply = f"Bảng giá gói tập tại HealthyGym: {plan_info}. Đặc biệt: Nhập mã GIAM10 (giảm 10%) hoặc HEALTHY20 (giảm 20% tối đa 500k) khi đăng ký nhé!"
    elif "lịch" in msg_lower or "lớp" in msg_lower or "yoga" in msg_lower or "hiit" in msg_lower:
        class_info = "; ".join([f"{c.name} ({c.schedule_time} - {c.room})" for c in classes])
        reply = f"Lịch các lớp học hiện tại: {class_info}. Lưu ý bạn cần có thẻ hội viên còn hạn để đặt chỗ nhé!"
    elif "bảo lưu" in msg_lower or "tạm dừng" in msg_lower:
        reply = "Hội viên có thẻ đang hoạt động có thể vào mục 'Tài khoản & Thẻ tập' để bấm Bảo lưu thẻ từ 1 đến 60 ngày. Hệ thống sẽ tự động cộng bù số ngày bảo lưu vào hạn thẻ của bạn!"
    elif "giảm cân" in msg_lower or "mỡ" in msg_lower or "tăng cơ" in msg_lower:
        reply = "Gợi ý lộ trình chuẩn: Kết hợp 3 buổi tập tạ (Strength) + 2 buổi HIIT/Boxing mỗi tuần, ngủ đủ 7-8 tiếng và nạp 1.8g Protein/kg cân nặng. Bạn nên chọn Gói 3 Tháng hoặc 6 Tháng có PT kèm 1-1!"
    else:
        reply = "Xin chào! Mình là Trợ lý AI của HealthyGym. Bạn có thể hỏi mình về: Giá gói tập & Mã giảm giá, Lịch lớp Yoga/HIIT/Boxing, Chính sách bảo lưu thẻ, hoặc Lộ trình tăng cơ giảm mỡ!"

    record = ChatMessage(username=req.username, user_message=req.message, bot_response=reply)
    db.add(record)
    db.commit()
    return {"reply": reply}
