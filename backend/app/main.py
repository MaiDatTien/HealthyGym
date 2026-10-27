from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import engine, Base, get_db, SessionLocal
from app.routers import (
    auth,
    listings,
    search,
    interactions,
    recommendations,
    chat,
    admin,
    ai,
    progress,
    pt,
    ai_plus,
    memberships,
    pt_ops,
    groupx,
    gym_ops,
    engagement,
    equipment,
)
from app.services.seed_data import seed_initial_data
from app.migrations import run_lightweight_migrations

# Import models để Base.metadata nhận diện đầy đủ bảng trước khi create_all
from app import models  # noqa: F401

Base.metadata.create_all(bind=engine)
# Bổ sung cột mới cho các bảng đã tồn tại từ bản cài đặt trước đó
run_lightweight_migrations(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="HealthyGym — All-in-One Smart Gym ERP & AI Fitness Coach",
    description=(
        "Hệ thống Quản trị Phòng Gym Toàn Diện & Huấn luyện viên AI Cá nhân hoá.\n\n"
        "**7 phân hệ nghiệp vụ:**\n"
        "- `/ai`, `/ai-plus` — AI Smart Coach: sàng lọc PAR-Q, chẩn đoán thể trạng, "
        "InBody, lịch tập, dinh dưỡng, phục hồi, chu kỳ hóa\n"
        "- `/memberships` — Vòng đời hợp đồng: bảo lưu, chuyển nhượng, nâng cấp, "
        "trả góp, leads tập thử, ví trả trước\n"
        "- `/pt-ops` — Nghiệp vụ PT: gói buổi tập, ca làm việc, chống gian lận "
        "xác nhận kép, lương hoa hồng\n"
        "- `/groupx` — Lớp nhóm: lịch học, chọn vị trí, danh sách chờ tự động\n"
        "- `/gym-ops` — Vận hành: QR động check-in, tủ đồ & khăn, POS Pro-Shop\n"
        "- `/engagement` — Gamification & CRM: streak, huy hiệu, thử thách, "
        "điểm thưởng, churn prediction\n"
        "- `/equipment` — Thiết bị: mã QR máy, vòng đời bảo trì, đồng bộ AI Coach\n\n"
        "**6 vai trò:** guest · member · trainer · receptionist · facility_manager · admin\n\n"
        "**Tài khoản demo:** admin/123 · letan/123 · csvc/123 · hlv/123 · "
        "hoivien/123 · staff/123 (bí danh lễ tân)"
    ),
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.\d+\.\d+)(:[0-9]+)?$",
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(search.router)
app.include_router(interactions.router)
app.include_router(recommendations.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(ai.router)
app.include_router(ai_plus.router)
app.include_router(progress.router)
app.include_router(pt.router)
app.include_router(pt_ops.router)
app.include_router(memberships.router)
app.include_router(groupx.router)
app.include_router(gym_ops.router)
app.include_router(engagement.router)
app.include_router(equipment.router)

@app.get("/")
def root():
    return {"message": "API hệ thống quản lý phòng Gym HealthyGym (PostgreSQL) đang chạy"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "connected", "engine": str(engine.url.drivername)}
