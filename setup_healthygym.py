import os

FILES = {
    # ===================== BACKEND: FULL CRUD ADMIN API =====================
    "backend/app/routers/admin.py": """from fastapi import APIRouter, Depends, HTTPException
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
""",

    # ===================== FRONTEND: API HELPER (GET/POST/PUT/DELETE) =====================
    "frontend/lib/api.ts": """const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("hg_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchGymData(endpoint: string) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Lỗi tải dữ liệu: ${endpoint}`);
  return data;
}

export async function postGymData(endpoint: string, body: unknown = {}) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Có lỗi xảy ra");
  return data;
}

export async function putGymData(endpoint: string, body: unknown = {}) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Không thể cập nhật dữ liệu");
  return data;
}

export async function deleteGymData(endpoint: string) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Không thể xóa dữ liệu");
  return data;
}
""",

    # ===================== FRONTEND: NAVIGATION BAR (MULTI-PAGE) =====================
    "frontend/components/Nav.tsx": """"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Nav() {
  const pathname = usePathname();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const saved = localStorage.getItem("hg_user");
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch {}
    }
  }, [pathname]);

  const handleLogout = () => {
    localStorage.removeItem("hg_token");
    localStorage.removeItem("hg_user");
    window.location.href = "/login";
  };

  const navItems = [
    { href: "/", label: "Trang chủ" },
    { href: "/plans", label: "Gói Hội Viên" },
    { href: "/schedule", label: "Lịch Lớp Tập" },
    { href: "/facilities", label: "CSVC & HLV" },
    { href: "/branches", label: "Chi Nhánh" },
    { href: "/chat", label: "Trợ Lý AI" },
  ];

  return (
    <header className="hg-navbar">
      <div className="hg-nav-inner">
        <Link href="/" className="hg-logo">
          <span className="hg-logo-icon">🌿</span>
          <span>Healthy<strong>Gym</strong></span>
        </Link>

        <nav className="hg-nav-menu">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`hg-nav-link ${pathname === item.href ? "active" : ""}`}
            >
              {item.label}
            </Link>
          ))}
          {user && (
            <Link
              href="/profile"
              className={`hg-nav-link ${pathname === "/profile" ? "active" : ""}`}
            >
              Thẻ Của Tôi
            </Link>
          )}
          {user && (user.role === "admin" || user.role === "staff") && (
            <Link
              href="/admin"
              className={`hg-nav-link hg-admin-badge ${pathname === "/admin" ? "active" : ""}`}
            >
              ⚙️ Quản Trị Hệ Thống
            </Link>
          )}
        </nav>

        <div className="hg-nav-auth">
          {user ? (
            <div style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
              <Link href="/profile" className="hg-user-chip">
                <span>👤 {user.full_name}</span>
                <small>{user.role.toUpperCase()}</small>
              </Link>
              <button onClick={handleLogout} className="hg-btn-ghost">
                Thoát
              </button>
            </div>
          ) : (
            <Link href="/login" className="hg-btn-emerald">
              Đăng Nhập / Tham Gia
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
""",

    # ===================== FRONTEND: FRESH MINT & CORAL WELLNESS CSS =====================
    "frontend/app/globals.css": """* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
body {
  font-family: "Plus Jakarta Sans", "Inter", system-ui, -apple-system, sans-serif;
  background: linear-gradient(180deg, #f0fdf4 0%, #f8fafc 40%, #fff1f2 100%);
  color: #0f172a;
  line-height: 1.65;
  min-height: 100vh;
}
a {
  color: inherit;
  text-decoration: none;
}

/* NAVBAR TƯƠI SÁNG HIỆN ĐẠI */
.hg-navbar {
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(16, 185, 129, 0.16);
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 0.85rem 1.5rem;
}
.hg-nav-inner {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}
.hg-logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.55rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.5px;
}
.hg-logo strong {
  color: #0d9488;
}
.hg-logo-icon {
  background: linear-gradient(135deg, #10b981, #0d9488);
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 1.2rem;
  box-shadow: 0 6px 14px rgba(16, 185, 129, 0.25);
}
.hg-nav-menu {
  display: flex;
  gap: 0.35rem;
  align-items: center;
  flex-wrap: wrap;
}
.hg-nav-link {
  padding: 0.5rem 0.95rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.92rem;
  color: #475569;
  transition: all 0.2s;
}
.hg-nav-link:hover {
  color: #0d9488;
  background: #f0fdf4;
}
.hg-nav-link.active {
  background: #ccfbf1;
  color: #0f766e;
  font-weight: 700;
}
.hg-admin-badge {
  background: #ffe4e6;
  color: #be123c !important;
  font-weight: 700;
}
.hg-admin-badge.active {
  background: #f43f5e !important;
  color: #ffffff !important;
}
.hg-user-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #f0fdf4;
  border: 1px solid #a7f3d0;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  color: #065f46;
}
.hg-user-chip small {
  background: #10b981;
  color: #fff;
  padding: 2px 7px;
  border-radius: 99px;
  font-size: 0.7rem;
}

/* BUTTONS */
.hg-btn-emerald, .btn-primary, .btn-cyan {
  background: linear-gradient(135deg, #10b981 0%, #0d9488 100%);
  color: #ffffff;
  border: none;
  padding: 0.7rem 1.35rem;
  border-radius: 14px;
  font-weight: 700;
  font-size: 0.92rem;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(13, 148, 136, 0.22);
  transition: transform 0.15s, box-shadow 0.2s;
  display: inline-block;
  text-align: center;
}
.hg-btn-emerald:hover, .btn-primary:hover, .btn-cyan:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(13, 148, 136, 0.32);
}
.hg-btn-coral, .btn-orange {
  background: linear-gradient(135deg, #f43f5e 0%, #fb7185 100%);
  color: #ffffff;
  border: none;
  padding: 0.7rem 1.35rem;
  border-radius: 14px;
  font-weight: 700;
  font-size: 0.92rem;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(244, 63, 94, 0.25);
  transition: transform 0.15s;
}
.hg-btn-coral:hover, .btn-orange:hover {
  transform: translateY(-2px);
}
.hg-btn-ghost, .btn-outline-sm {
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  color: #475569;
  padding: 0.5rem 1rem;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.15s;
}
.hg-btn-ghost:hover, .btn-outline-sm:hover {
  border-color: #0d9488;
  color: #0d9488;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2.2rem 1.5rem 5rem;
}

/* HERO SECTION TƯƠI SÁNG ĐỘC BẢN */
.hg-hero {
  background: linear-gradient(135deg, #ffffff 0%, #ecfdf5 55%, #ccfbf1 100%);
  border: 1px solid #a7f3d0;
  border-radius: 32px;
  padding: 3.5rem 3rem;
  margin-bottom: 3rem;
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 2.5rem;
  align-items: center;
  box-shadow: 0 20px 50px rgba(13, 148, 136, 0.08);
}
@media (max-width: 900px) {
  .hg-hero {
    grid-template-columns: 1fr;
    padding: 2rem 1.5rem;
  }
}
.hg-pill-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: #ffffff;
  color: #0f766e;
  border: 1px solid #99f6e4;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 700;
  margin-bottom: 1.2rem;
}
.hg-hero h1 {
  font-size: 2.85rem;
  font-weight: 900;
  line-height: 1.15;
  color: #0f172a;
  margin-bottom: 1rem;
  letter-spacing: -1px;
}
.hg-hero h1 span {
  background: linear-gradient(135deg, #0d9488, #10b981);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hg-page-header {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 24px;
  padding: 2.2rem 2.5rem;
  margin-bottom: 2.2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.03);
}
.hg-page-header h1 {
  font-size: 2rem;
  font-weight: 800;
  color: #0f172a;
}

/* CARDS & BENTO GRID */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 1.6rem;
  margin-bottom: 2.5rem;
}
.card, .tng-plan-card {
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  border-radius: 24px;
  padding: 1.8rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform 0.25s, box-shadow 0.25s, border-color 0.25s;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.04);
}
.card:hover, .tng-plan-card:hover {
  transform: translateY(-5px);
  border-color: #5eead4;
  box-shadow: 0 20px 40px rgba(13, 148, 136, 0.1);
}
.tng-plan-popular {
  border: 2.5px solid #0d9488;
  background: linear-gradient(180deg, #f0fdfa 0%, #ffffff 45%);
}
.tng-popular-ribbon {
  background: linear-gradient(90deg, #0d9488, #10b981);
  color: #ffffff;
  font-weight: 800;
  font-size: 0.78rem;
  padding: 6px 14px;
  border-radius: 999px;
  align-self: center;
  margin-bottom: 1rem;
}
.tng-normal-ribbon {
  background: #f1f5f9;
  color: #475569;
  font-weight: 700;
  font-size: 0.78rem;
  padding: 6px 14px;
  border-radius: 999px;
  align-self: center;
  margin-bottom: 1rem;
}
.tng-plan-title {
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
  text-align: center;
}
.tng-plan-scope {
  text-align: center;
  color: #64748b;
  font-size: 0.88rem;
  margin-bottom: 0.8rem;
}
.tng-price-box {
  text-align: center;
  margin: 0.5rem 0;
}
.tng-price-num {
  font-size: 2.3rem;
  font-weight: 900;
  color: #0d9488;
}
.tng-price-unit {
  font-size: 0.9rem;
  color: #64748b;
  font-weight: 600;
}
.tng-sub-price {
  text-align: center;
  font-size: 0.84rem;
  color: #f43f5e;
  font-weight: 600;
  margin-bottom: 1.2rem;
}
.tng-btn-join {
  background: linear-gradient(135deg, #0d9488, #10b981);
  color: #fff;
  border: none;
  padding: 0.85rem;
  border-radius: 14px;
  font-weight: 800;
  cursor: pointer;
  width: 100%;
}

.chip {
  display: inline-block;
  background: #ccfbf1;
  color: #0f766e;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 700;
}
.input-box {
  padding: 0.75rem 1rem;
  border-radius: 12px;
  border: 1.5px solid #cbd5e1;
  background: #ffffff;
  color: #0f172a;
  width: 100%;
  margin-bottom: 0.8rem;
  font-size: 0.94rem;
}
.input-box:focus {
  outline: none;
  border-color: #0d9488;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12);
}
.divider {
  height: 1px;
  background: #e2e8f0;
  margin: 1rem 0;
}
.benefit-list {
  list-style: none;
  font-size: 0.92rem;
  color: #334155;
}
.benefit-list li {
  margin-bottom: 0.55rem;
  display: flex;
  align-items: flex-start;
}
.stats-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 1.25rem;
  margin-bottom: 2.5rem;
}
.stat-item {
  background: #ffffff;
  padding: 1.4rem 1.6rem;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.03);
}
.progress-bar {
  width: 100%;
  height: 8px;
  background: #f1f5f9;
  border-radius: 99px;
  overflow: hidden;
  margin: 0.6rem 0;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #0d9488);
}
.table-wrap {
  overflow-x: auto;
  background: #ffffff;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  padding: 1.25rem;
  margin-bottom: 2rem;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.03);
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}
th, td {
  text-align: left;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #f1f5f9;
}
th {
  color: #0f766e;
  font-weight: 800;
  background: #f8fafc;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(6px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 300;
  padding: 1rem;
}
.modal-card {
  background: #ffffff;
  border-radius: 26px;
  max-width: 520px;
  width: 100%;
  padding: 2.2rem;
  box-shadow: 0 25px 60px rgba(15, 23, 42, 0.25);
}
""",

    # ===================== TRANG 1: TRANG CHỦ (/) =====================
    "frontend/app/page.tsx": """"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchGymData, postGymData } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default function HomePage() {
  const [reports, setReports] = useState<any>(null);
  const [trialName, setTrialName] = useState("");
  const [trialPhone, setTrialPhone] = useState("");
  const [toast, setToast] = useState<string>("");

  useEffect(() => {
    fetchGymData("/admin/reports").then(setReports).catch(() => {});
  }, []);

  const handleTrial = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await postGymData("/interactions/free-trial", {
        full_name: trialName,
        phone: trialPhone,
      });
      setToast(res.message);
      setTrialName("");
      setTrialPhone("");
    } catch (err: any) {
      setToast(err.message);
    }
  };

  return (
    <div>
      {toast && (
        <div
          style={{
            background: "#0d9488",
            color: "#fff",
            padding: "1rem 1.5rem",
            borderRadius: "16px",
            marginBottom: "1.5rem",
            fontWeight: 700,
          }}
        >
          ✨ {toast}
        </div>
      )}

      <section className="hg-hero">
        <div>
          <span className="hg-pill-tag">🌱 Không Gian Tập Luyện Xanh & Hiện Đại 24/7</span>
          <h1>
            Khởi Đầu Hành Trình <span>Khỏe Đẹp Toàn Diện</span> Cùng HealthyGym
          </h1>
          <p style={{ color: "#475569", fontSize: "1.06rem", marginBottom: "1.8rem" }}>
            Hệ thống quản lý thẻ tập thông minh, cá nhân hóa lịch học Yoga, HIIT, Boxing và theo dõi tiến độ tập luyện của riêng bạn mỗi ngày.
          </p>
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            <Link href="/plans" className="hg-btn-emerald" style={{ padding: "0.9rem 1.8rem" }}>
              Xem Bảng Giá Gói Tập →
            </Link>
            <Link href="/schedule" className="hg-btn-ghost" style={{ padding: "0.9rem 1.6rem" }}>
              📅 Xem Lịch Lớp Học
            </Link>
          </div>
        </div>

        <div className="card" style={{ border: "2px solid #99f6e4" }}>
          <span className="chip" style={{ alignSelf: "flex-start", marginBottom: "0.6rem" }}>
            🎁 QUÀ TẶNG THÀNH VIÊN MỚI
          </span>
          <h3 style={{ fontSize: "1.45rem", marginBottom: "0.4rem" }}>
            Trải Nghiệm 7 Ngày Miễn Phí
          </h3>
          <p style={{ color: "#64748b", fontSize: "0.9rem", marginBottom: "1.2rem" }}>
            Để lại họ tên và số điện thoại để kích hoạt ngay 7 ngày tập thử toàn bộ máy Cardio, Tạ và lớp Yoga.
          </p>
          <form onSubmit={handleTrial}>
            <input
              className="input-box"
              placeholder="Họ và tên của bạn *"
              value={trialName}
              onChange={(e) => setTrialName(e.target.value)}
              required
            />
            <input
              className="input-box"
              placeholder="Số điện thoại liên hệ *"
              value={trialPhone}
              onChange={(e) => setTrialPhone(e.target.value)}
              required
            />
            <button type="submit" className="hg-btn-coral" style={{ width: "100%", padding: "0.85rem" }}>
              Nhận Vé Tập Thử 7 Ngày
            </button>
          </form>
        </div>
      </section>

      {reports && (
        <div className="stats-bar">
          <div className="stat-item">
            <div style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 600 }}>Hội viên đang hoạt động</div>
            <strong style={{ fontSize: "1.8rem", color: "#0d9488" }}>
              {reports.active_members} / {reports.total_members}
            </strong>
          </div>
          <div className="stat-item">
            <div style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 600 }}>Lượt đặt chỗ lớp học</div>
            <strong style={{ fontSize: "1.8rem", color: "#0f172a" }}>{reports.total_bookings}</strong>
          </div>
          <div className="stat-item">
            <div style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 600 }}>Huấn luyện viên chuẩn Quốc tế</div>
            <strong style={{ fontSize: "1.8rem", color: "#0f172a" }}>{reports.total_trainers}</strong>
          </div>
          <div className="stat-item">
            <div style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 600 }}>Tổng doanh thu hệ thống</div>
            <strong style={{ fontSize: "1.8rem", color: "#f43f5e" }}>
              {formatCurrency(reports.total_revenue)}
            </strong>
          </div>
        </div>
      )}

      <h2 style={{ fontSize: "1.75rem", fontWeight: 800, marginBottom: "1.2rem" }}>
        Khám Phá Các Chuyên Trang Của HealthyGym
      </h2>
      <div className="grid">
        <Link href="/plans" className="card">
          <div>
            <span className="chip">BẢNG GIÁ MINH BẠCH</span>
            <h3 style={{ margin: "0.7rem 0" }}>💎 Gói Tập Hội Viên</h3>
            <p style={{ color: "#64748b", fontSize: "0.92rem" }}>
              So sánh chi tiết các gói 1 tháng, 6 tháng, 12 tháng và áp mã giảm giá trực tuyến.
            </p>
          </div>
          <span style={{ color: "#0d9488", fontWeight: 700, marginTop: "1rem" }}>Đi tới trang Gói tập →</span>
        </Link>

        <Link href="/schedule" className="card">
          <div>
            <span className="chip">ĐẶT CHỖ REALTIME</span>
            <h3 style={{ margin: "0.7rem 0" }}>📅 Lịch Lớp Tập Nhóm</h3>
            <p style={{ color: "#64748b", fontSize: "0.92rem" }}>
              Theo dõi số chỗ trống và đặt lịch các lớp Yoga, HIIT, Boxing, Strength chỉ với 1 chạm.
            </p>
          </div>
          <span style={{ color: "#0d9488", fontWeight: 700, marginTop: "1rem" }}>Đi tới Lịch lớp học →</span>
        </Link>

        <Link href="/facilities" className="card">
          <div>
            <span className="chip">TRANG THIẾT BỊ & PT</span>
            <h3 style={{ margin: "0.7rem 0" }}>🏋️ Cơ Sở Vật Chất & HLV</h3>
            <p style={{ color: "#64748b", fontSize: "0.92rem" }}>
              Khám phá dàn máy Cardio, khu tạ chuẩn Olympic cùng đội ngũ Huấn luyện viên cá nhân.
            </p>
          </div>
          <span style={{ color: "#0d9488", fontWeight: 700, marginTop: "1rem" }}>Xem CSVC & HLV →</span>
        </Link>

        <Link href="/branches" className="card">
          <div>
            <span className="chip">MẠNG LƯỚI TOÀN QUỐC</span>
            <h3 style={{ margin: "0.7rem 0" }}>📍 Hệ Thống Chi Nhánh</h3>
            <p style={{ color: "#64748b", fontSize: "0.92rem" }}>
              Tra cứu địa chỉ, hotline và giờ mở cửa của các cơ sở tại TP.HCM, Đà Nẵng, Cần Thơ, Đồng Nai.
            </p>
          </div>
          <span style={{ color: "#0d9488", fontWeight: 700, marginTop: "1rem" }}>Tìm phòng tập gần bạn →</span>
        </Link>
      </div>
    </div>
  );
}
""",

    # ===================== TRANG 2: GÓI HỘI VIÊN (/plans) =====================
    "frontend/app/plans/page.tsx": """"use client";
import React, { useEffect, useState } from "react";
import ListingCard from "@/components/ListingCard";
import { fetchGymData, postGymData } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default function PlansPage() {
  const [plans, setPlans] = useState<any[]>([]);
  const [checkoutPlan, setCheckoutPlan] = useState<any>(null);
  const [voucherCode, setVoucherCode] = useState("GIAM10");
  const [voucherPreview, setVoucherPreview] = useState<any>(null);
  const [paymentMethod, setPaymentMethod] = useState("Chuyển khoản QR");
  const [msg, setMsg] = useState<{ type: string; text: string } | null>(null);

  useEffect(() => {
    fetchGymData("/listings/plans").then(setPlans).catch(() => {});
  }, []);

  const handlePreviewVoucher = async () => {
    if (!checkoutPlan || !voucherCode.trim()) return;
    try {
      const res = await fetchGymData(
        `/interactions/vouchers/validate?code=${encodeURIComponent(voucherCode)}&plan_id=${checkoutPlan.id}`
      );
      setVoucherPreview(res);
    } catch (err: any) {
      setVoucherPreview(null);
      setMsg({ type: "err", text: err.message });
    }
  };

  const handleConfirmCheckout = async () => {
    if (!checkoutPlan) return;
    try {
      const res = await postGymData("/interactions/orders", {
        plan_id: checkoutPlan.id,
        voucher_code: voucherCode,
        payment_method: paymentMethod,
      });
      setMsg({ type: "ok", text: res.message });
      setCheckoutPlan(null);
      setVoucherPreview(null);
    } catch (err: any) {
      setMsg({ type: "err", text: err.message });
    }
  };

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">LINH HOẠT & MINH BẠCH</span>
          <h1 style={{ marginTop: "0.4rem" }}>Bảng Giá Gói Hội Viên HealthyGym</h1>
          <p style={{ color: "#64748b" }}>
            Nhập mã ưu đãi <strong>GIAM10</strong> (giảm 10%) hoặc <strong>HEALTHY20</strong> (giảm 20%) khi thanh toán.
          </p>
        </div>
      </div>

      {msg && (
        <div
          style={{
            background: msg.type === "ok" ? "#0d9488" : "#f43f5e",
            color: "#fff",
            padding: "1rem 1.4rem",
            borderRadius: "14px",
            marginBottom: "1.5rem",
            fontWeight: 700,
          }}
        >
          {msg.text}
        </div>
      )}

      <div className="grid">
        {plans.map((plan) => (
          <ListingCard
            key={plan.id}
            plan={plan}
            onSelectPlan={(p) => {
              setCheckoutPlan(p);
              setVoucherPreview(null);
            }}
          />
        ))}
      </div>

      {checkoutPlan && (
        <div className="modal-backdrop" onClick={() => setCheckoutPlan(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: "1.35rem", fontWeight: 800 }}>Đăng Ký: {checkoutPlan.name}</h3>
            <p style={{ color: "#64748b", marginBottom: "1rem" }}>
              Thời hạn cộng thêm vào thẻ: <strong>{checkoutPlan.duration_days} ngày</strong>
            </p>
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Mã giảm giá</label>
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.3rem" }}>
              <input
                className="input-box"
                value={voucherCode}
                onChange={(e) => setVoucherCode(e.target.value.toUpperCase())}
              />
              <button type="button" className="hg-btn-emerald" style={{ height: "44px" }} onClick={handlePreviewVoucher}>
                Áp dụng
              </button>
            </div>
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Phương thức thanh toán</label>
            <select className="input-box" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
              <option value="Chuyển khoản QR">Chuyển khoản ngân hàng (VietQR)</option>
              <option value="Thẻ quốc tế VISA/Mastercard">Thẻ JCB / VISA / Mastercard</option>
              <option value="Ví MoMo">Ví điện tử MoMo</option>
            </select>

            <div style={{ background: "#f8fafc", padding: "1rem", borderRadius: "14px", margin: "1rem 0" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Giá niêm yết:</span>
                <strong>{formatCurrency(checkoutPlan.price)}</strong>
              </div>
              {voucherPreview && (
                <div style={{ display: "flex", justifyContent: "space-between", color: "#0d9488" }}>
                  <span>Giảm giá ({voucherPreview.code}):</span>
                  <strong>- {formatCurrency(voucherPreview.discount_amount)}</strong>
                </div>
              )}
              <div className="divider" />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "1.2rem", fontWeight: 800 }}>
                <span>Thành tiền:</span>
                <span style={{ color: "#f43f5e" }}>
                  {formatCurrency(voucherPreview ? voucherPreview.final_price : checkoutPlan.price)}
                </span>
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button className="hg-btn-ghost" style={{ flex: 1 }} onClick={() => setCheckoutPlan(null)}>
                Đóng
              </button>
              <button className="hg-btn-emerald" style={{ flex: 2 }} onClick={handleConfirmCheckout}>
                Xác Nhận Thanh Toán
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
""",

    # ===================== TRANG 3: LỊCH LỚP TẬP (/schedule) =====================
    "frontend/app/schedule/page.tsx": """"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";

export default function SchedulePage() {
  const [classes, setClasses] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [keyword, setKeyword] = useState("");
  const [msg, setMsg] = useState<{ type: string; text: string } | null>(null);

  const loadClasses = () => {
    fetchGymData("/listings/classes").then(setClasses).catch(() => {});
  };

  useEffect(() => {
    loadClasses();
  }, []);

  const handleBook = async (classId: number) => {
    try {
      const res = await postGymData("/interactions/bookings", {
        gym_class_id: classId,
        note: "Đặt lịch từ trang Schedule",
      });
      setMsg({ type: "ok", text: res.message });
      loadClasses();
    } catch (err: any) {
      setMsg({ type: "err", text: err.message });
    }
  };

  const filtered = classes.filter((c) => {
    const matchCat = selectedCategory === "ALL" || c.category === selectedCategory;
    const matchKw =
      c.name.toLowerCase().includes(keyword.toLowerCase()) ||
      c.trainer_name.toLowerCase().includes(keyword.toLowerCase());
    return matchCat && matchKw;
  });

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">GROUP X & STUDIO</span>
          <h1 style={{ marginTop: "0.4rem" }}>Lịch Lớp Tập Nhóm & Đặt Chỗ</h1>
          <p style={{ color: "#64748b" }}>
            Chủ động đặt lịch trước để giữ chỗ cho các lớp Yoga, HIIT, Boxing và Strength.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {["ALL", "Yoga", "HIIT", "Boxing", "Strength"].map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={selectedCategory === cat ? "hg-btn-emerald" : "hg-btn-ghost"}
            >
              {cat === "ALL" ? "Tất cả" : cat}
            </button>
          ))}
        </div>
      </div>

      {msg && (
        <div
          style={{
            background: msg.type === "ok" ? "#0d9488" : "#f43f5e",
            color: "#fff",
            padding: "1rem 1.4rem",
            borderRadius: "14px",
            marginBottom: "1.5rem",
            fontWeight: 700,
          }}
        >
          {msg.text}
        </div>
      )}

      <input
        className="input-box"
        style={{ maxWidth: "360px", marginBottom: "1.5rem" }}
        placeholder="🔍 Tìm theo tên lớp hoặc Huấn luyện viên..."
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
      />

      <div className="grid">
        {filtered.map((c) => {
          const percent = Math.min(100, Math.round((c.enrolled_count / c.capacity) * 100));
          return (
            <div key={c.id} className="card">
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="chip">{c.category}</span>
                  <strong style={{ fontSize: "0.85rem", color: c.available_spots > 0 ? "#0d9488" : "#f43f5e" }}>
                    Còn {c.available_spots}/{c.capacity} chỗ
                  </strong>
                </div>
                <h3 style={{ margin: "0.6rem 0", fontSize: "1.25rem" }}>{c.name}</h3>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${percent}%` }} />
                </div>
                <p style={{ fontSize: "0.9rem" }}>🕒 {c.schedule_time}</p>
                <p style={{ fontSize: "0.9rem" }}>📍 Phòng: {c.room} ({c.branch_name})</p>
                <p style={{ fontSize: "0.9rem" }}>💪 HLV: <strong>{c.trainer_name}</strong></p>
                <p style={{ color: "#64748b", fontSize: "0.88rem", marginTop: "0.5rem" }}>{c.description}</p>
              </div>
              <button
                className="hg-btn-emerald"
                style={{ width: "100%", marginTop: "1rem" }}
                disabled={c.available_spots <= 0}
                onClick={() => handleBook(c.id)}
              >
                {c.available_spots > 0 ? "Đặt Chỗ Lớp Này" : "Đã Đầy Chỗ"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
""",

    # ===================== TRANG 4: CƠ SỞ VẬT CHẤT & HLV (/facilities) =====================
    "frontend/app/facilities/page.tsx": """"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData } from "@/lib/api";

export default function FacilitiesPage() {
  const [facilities, setFacilities] = useState<any[]>([]);
  const [trainers, setTrainers] = useState<any[]>([]);

  useEffect(() => {
    fetchGymData("/listings/facilities").then(setFacilities).catch(() => {});
    fetchGymData("/listings/trainers").then(setTrainers).catch(() => {});
  }, []);

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">TRANG THIẾT BỊ & ĐỘI NGŨ CHUYÊN GIA</span>
          <h1 style={{ marginTop: "0.4rem" }}>Cơ Sở Vật Chất & Huấn Luyện Viên</h1>
          <p style={{ color: "#64748b" }}>
            Không gian tập luyện chuẩn quốc tế cùng đội ngũ PT giàu kinh nghiệm luôn sẵn sàng đồng hành cùng bạn.
          </p>
        </div>
      </div>

      <h2 style={{ fontSize: "1.5rem", fontWeight: 800, marginBottom: "1rem" }}>
        🏋️ Thiết Bị Tập Luyện & Tiện Ích Miễn Phí
      </h2>
      <div className="grid">
        {facilities.map((f) => (
          <div key={f.id} className="card">
            <div>
              <span className="chip">{f.category}</span>
              <h3 style={{ margin: "0.6rem 0" }}>{f.name}</h3>
              <p style={{ color: "#64748b", fontSize: "0.92rem" }}>{f.description}</p>
            </div>
            <div style={{ marginTop: "1rem", fontWeight: 700, color: "#0d9488" }}>
              ✓ {f.status} • Số lượng: {f.quantity}
            </div>
          </div>
        ))}
      </div>

      <h2 style={{ fontSize: "1.5rem", fontWeight: 800, marginBottom: "1rem" }}>
        🏆 Đội Ngũ Huấn Luyện Viên (Personal Trainers)
      </h2>
      <div className="grid">
        {trainers.map((t) => (
          <div key={t.id} className="card">
            <div>
              <span className="chip">{t.experience_years} năm kinh nghiệm</span>
              <h3 style={{ margin: "0.6rem 0" }}>{t.full_name}</h3>
              <p style={{ color: "#f43f5e", fontWeight: 700, fontSize: "0.92rem" }}>{t.specialty}</p>
              <p style={{ color: "#64748b", fontSize: "0.9rem", marginTop: "0.5rem" }}>{t.bio}</p>
            </div>
            <div style={{ marginTop: "1rem", fontSize: "0.88rem", color: "#475569" }}>
              📞 Liên hệ PT: <strong>{t.phone || "1900 636920"}</strong>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
""",

    # ===================== TRANG 5: CHI NHÁNH (/branches) =====================
    "frontend/app/branches/page.tsx": """"use client";
import React, { useEffect, useState } from "react";
import PropertyCard from "@/components/PropertyCard";
import { fetchGymData } from "@/lib/api";

export default function BranchesPage() {
  const [branches, setBranches] = useState<any[]>([]);
  const [city, setCity] = useState("ALL");

  useEffect(() => {
    fetchGymData("/listings/branches").then(setBranches).catch(() => {});
  }, []);

  const filtered = branches.filter((b) =>
    city === "ALL" ? true : b.name.includes(city) || b.address.includes(city)
  );

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">MỞ CỬA 24/7 TOÀN QUỐC</span>
          <h1 style={{ marginTop: "0.4rem" }}>Hệ Thống Phòng Tập HealthyGym</h1>
          <p style={{ color: "#64748b" }}>Tìm kiếm chi nhánh thuận tiện nhất cho việc đi lại của bạn.</p>
        </div>
        <select
          className="input-box"
          style={{ width: "240px", marginBottom: 0, fontWeight: 700 }}
          value={city}
          onChange={(e) => setCity(e.target.value)}
        >
          <option value="ALL">Tất cả Tỉnh / Thành phố</option>
          <option value="Hồ Chí Minh">TP. Hồ Chí Minh</option>
          <option value="Đà Nẵng">Đà Nẵng</option>
          <option value="Cần Thơ">Cần Thơ</option>
          <option value="Đồng Nai">Đồng Nai</option>
        </select>
      </div>

      <div className="grid">
        {filtered.map((b) => (
          <PropertyCard key={b.id} branch={b} />
        ))}
      </div>
    </div>
  );
}
""",

    # ===================== TRANG 6: HỒ SƠ & THẺ CỦA TÔI (/profile) =====================
    "frontend/app/profile/page.tsx": """"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default function ProfilePage() {
  const [user, setUser] = useState<any>(null);
  const [bookings, setBookings] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [freezeDays, setFreezeDays] = useState(14);
  const [msg, setMsg] = useState("");

  const loadProfile = () => {
    fetchGymData("/auth/me").then(setUser).catch(() => {});
    fetchGymData("/interactions/bookings/my").then(setBookings).catch(() => {});
    fetchGymData("/interactions/orders/my").then(setOrders).catch(() => {});
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleFreeze = async () => {
    try {
      const res = await postGymData("/interactions/freeze", { days: freezeDays });
      setMsg(res.message);
      loadProfile();
    } catch (err: any) {
      setMsg(err.message);
    }
  };

  const handleUnfreeze = async () => {
    try {
      const res = await postGymData("/interactions/unfreeze");
      setMsg(res.message);
      loadProfile();
    } catch (err: any) {
      setMsg(err.message);
    }
  };

  const handleCancelBooking = async (id: number) => {
    try {
      const res = await postGymData(`/interactions/bookings/${id}/cancel`);
      setMsg(res.message);
      loadProfile();
    } catch (err: any) {
      setMsg(err.message);
    }
  };

  if (!user) {
    return (
      <div className="card" style={{ maxWidth: "480px", margin: "2rem auto", textAlign: "center" }}>
        <h3>Vui lòng đăng nhập để xem Thẻ Hội Viên</h3>
        <a href="/login" className="hg-btn-emerald" style={{ marginTop: "1rem" }}>
          Đi tới trang Đăng nhập
        </a>
      </div>
    );
  }

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">HỒ SƠ CÁ NHÂN</span>
          <h1 style={{ marginTop: "0.4rem" }}>Xin chào, {user.full_name}</h1>
          <p style={{ color: "#64748b" }}>
            Gói hiện tại: <strong>{user.plan_name}</strong> • Trạng thái:{" "}
            <strong style={{ color: "#0d9488" }}>{user.member_status?.toUpperCase()}</strong> • Hạn thẻ:{" "}
            <strong>{user.expire_date || "Chưa kích hoạt"}</strong>
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
          {user.member_status === "frozen" ? (
            <button className="hg-btn-coral" onClick={handleUnfreeze}>
              🔥 Mở Khóa Thẻ Tập Ngay
            </button>
          ) : (
            <>
              <input
                type="number"
                min={1}
                max={60}
                className="input-box"
                style={{ width: "85px", marginBottom: 0 }}
                value={freezeDays}
                onChange={(e) => setFreezeDays(Number(e.target.value))}
              />
              <button className="hg-btn-ghost" onClick={handleFreeze}>
                ❄️ Bảo lưu thẻ ({freezeDays} ngày)
              </button>
            </>
          )}
        </div>
      </div>

      {msg && (
        <div
          style={{
            background: "#0d9488",
            color: "#fff",
            padding: "1rem 1.4rem",
            borderRadius: "14px",
            marginBottom: "1.5rem",
            fontWeight: 700,
          }}
        >
          {msg}
        </div>
      )}

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="table-wrap">
          <h3 style={{ marginBottom: "1rem" }}>📅 Lịch Lớp Đã Đặt ({bookings.length})</h3>
          <table>
            <thead>
              <tr>
                <th>Lớp học</th>
                <th>Thời gian</th>
                <th>Trạng thái</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {bookings.map((b) => (
                <tr key={b.id}>
                  <td><strong>{b.class_name}</strong></td>
                  <td>{b.schedule_time}</td>
                  <td><span className="chip">{b.status}</span></td>
                  <td>
                    {b.status === "confirmed" && (
                      <button className="hg-btn-ghost" onClick={() => handleCancelBooking(b.id)}>
                        Hủy
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="table-wrap">
          <h3 style={{ marginBottom: "1rem" }}>🧾 Hóa Đơn Gói Tập ({orders.length})</h3>
          <table>
            <thead>
              <tr>
                <th>Gói đăng ký</th>
                <th>Đã giảm</th>
                <th>Thực thu</th>
                <th>Thanh toán</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td><strong>{o.plan_name}</strong></td>
                  <td>{formatCurrency(o.discount_amount || 0)}</td>
                  <td style={{ color: "#0d9488", fontWeight: 800 }}>{formatCurrency(o.total_amount)}</td>
                  <td>{o.payment_method}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
""",

    # ===================== TRANG 7: TRANG QUẢN TRỊ ADMIN FULL CRUD (/admin) =====================
    "frontend/app/admin/page.tsx": """"use client";
import React, { useEffect, useState } from "react";
import { fetchGymData, postGymData, putGymData, deleteGymData } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default function AdminPortalPage() {
  const [tab, setTab] = useState<"members" | "plans" | "classes" | "trainers" | "branches" | "facilities">("plans");
  const [members, setMembers] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [trainers, setTrainers] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [facilities, setFacilities] = useState<any[]>([]);
  const [msg, setMsg] = useState("");

  // State cho Form Gói tập (Thêm / Sửa)
  const [editingPlanId, setEditingPlanId] = useState<number | null>(null);
  const [planForm, setPlanForm] = useState({
    name: "",
    duration_days: 30,
    price: 399000,
    benefits: "Tập 24/7, Miễn phí lớp nhóm, Nước uống & Gửi xe",
    includes_pt: false,
    is_popular: false,
  });

  // State cho Form Lớp học (Thêm / Sửa)
  const [editingClassId, setEditingClassId] = useState<number | null>(null);
  const [classForm, setClassForm] = useState({
    name: "",
    category: "Yoga",
    schedule_time: "Thứ 2, 4, 6 (18:00 - 19:00)",
    room: "Studio 1",
    capacity: 25,
    description: "",
  });

  // State cho Form Huấn luyện viên (Thêm / Sửa)
  const [editingTrainerId, setEditingTrainerId] = useState<number | null>(null);
  const [trainerForm, setTrainerForm] = useState({
    full_name: "",
    specialty: "Bodybuilding & Tăng cơ",
    phone: "0909123456",
    experience_years: 4,
    bio: "",
  });

  // State cho Form Chi nhánh (Thêm / Sửa)
  const [editingBranchId, setEditingBranchId] = useState<number | null>(null);
  const [branchForm, setBranchForm] = useState({
    name: "",
    address: "",
    phone: "1900 636920",
    opening_hours: "Mở cửa 24/7",
  });

  // State cho Form Thiết bị CSVC (Thêm / Sửa)
  const [editingFacilityId, setEditingFacilityId] = useState<number | null>(null);
  const [facilityForm, setFacilityForm] = useState({
    name: "",
    category: "Cardio",
    quantity: 15,
    status: "Hoạt động tốt",
    description: "",
  });

  // State cho Form Hội viên (Thêm / Sửa)
  const [editingMemberId, setEditingMemberId] = useState<number | null>(null);
  const [memberForm, setMemberForm] = useState({
    full_name: "",
    phone: "",
    email: "",
    status: "active",
    expire_date: "2027-01-01",
  });

  const loadAll = () => {
    fetchGymData("/admin/members").then(setMembers).catch(() => {});
    fetchGymData("/listings/plans").then(setPlans).catch(() => {});
    fetchGymData("/listings/classes").then(setClasses).catch(() => {});
    fetchGymData("/listings/trainers").then(setTrainers).catch(() => {});
    fetchGymData("/listings/branches").then(setBranches).catch(() => {});
    fetchGymData("/listings/facilities").then(setFacilities).catch(() => {});
  };

  useEffect(() => {
    loadAll();
  }, []);

  const notify = (text: string) => {
    setMsg(text);
    setTimeout(() => setMsg(""), 4500);
    loadAll();
  };

  // Xử lý lưu Gói tập
  const savePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingPlanId) {
        await putGymData(`/admin/plans/${editingPlanId}`, planForm);
        notify("✅ Đã cập nhật gói tập!");
      } else {
        await postGymData("/admin/plans", planForm);
        notify("✅ Đã thêm gói tập mới!");
      }
      setEditingPlanId(null);
      setPlanForm({ name: "", duration_days: 30, price: 399000, benefits: "", includes_pt: false, is_popular: false });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  // Xử lý lưu Lớp học
  const saveClass = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingClassId) {
        await putGymData(`/admin/classes/${editingClassId}`, classForm);
        notify("✅ Đã cập nhật lớp học!");
      } else {
        await postGymData("/admin/classes", classForm);
        notify("✅ Đã thêm lớp học mới!");
      }
      setEditingClassId(null);
      setClassForm({ name: "", category: "Yoga", schedule_time: "", room: "Studio 1", capacity: 25, description: "" });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  // Xử lý lưu HLV
  const saveTrainer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingTrainerId) {
        await putGymData(`/admin/trainers/${editingTrainerId}`, trainerForm);
        notify("✅ Đã cập nhật Huấn luyện viên!");
      } else {
        await postGymData("/admin/trainers", trainerForm);
        notify("✅ Đã thêm Huấn luyện viên mới!");
      }
      setEditingTrainerId(null);
      setTrainerForm({ full_name: "", specialty: "", phone: "", experience_years: 4, bio: "" });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  // Xử lý lưu Chi nhánh
  const saveBranch = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingBranchId) {
        await putGymData(`/admin/branches/${editingBranchId}`, branchForm);
        notify("✅ Đã cập nhật chi nhánh!");
      } else {
        await postGymData("/admin/branches", branchForm);
        notify("✅ Đã thêm chi nhánh mới!");
      }
      setEditingBranchId(null);
      setBranchForm({ name: "", address: "", phone: "1900 636920", opening_hours: "Mở cửa 24/7" });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  // Xử lý lưu CSVC
  const saveFacility = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingFacilityId) {
        await putGymData(`/admin/facilities/${editingFacilityId}`, facilityForm);
        notify("✅ Đã cập nhật thiết bị!");
      } else {
        await postGymData("/admin/facilities", facilityForm);
        notify("✅ Đã thêm thiết bị mới!");
      }
      setEditingFacilityId(null);
      setFacilityForm({ name: "", category: "Cardio", quantity: 10, status: "Hoạt động tốt", description: "" });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  // Xử lý lưu Hội viên
  const saveMember = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...memberForm,
        expire_date: memberForm.expire_date ? memberForm.expire_date : null,
      };
      if (editingMemberId) {
        await putGymData(`/admin/members/${editingMemberId}`, payload);
        notify("✅ Đã cập nhật thông tin hội viên!");
      } else {
        await postGymData("/admin/members", payload);
        notify("✅ Đã thêm hội viên mới!");
      }
      setEditingMemberId(null);
      setMemberForm({ full_name: "", phone: "", email: "", status: "active", expire_date: "2027-01-01" });
    } catch (err: any) {
      notify(`⚠️ ${err.message}`);
    }
  };

  return (
    <div>
      <div className="hg-page-header">
        <div>
          <span className="chip">TRUNG TÂM QUẢN TRỊ VIÊN (ADMIN / 123)</span>
          <h1 style={{ marginTop: "0.4rem" }}>⚙️ Quản Lý Toàn Hệ Thống (Thêm • Sửa • Xóa)</h1>
          <p style={{ color: "#64748b" }}>
            Chọn từng phân mục bên dưới để thêm mới, chỉnh sửa hoặc xóa dữ liệu trực tiếp trong PostgreSQL.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {[
            { id: "plans", label: "💎 Gói Tập" },
            { id: "classes", label: "📅 Lớp Học" },
            { id: "trainers", label: "🏆 Huấn Luyện Viên" },
            { id: "branches", label: "📍 Chi Nhánh" },
            { id: "facilities", label: "🏋️ Thiết Bị CSVC" },
            { id: "members", label: "👥 Hội Viên & Check-in" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={tab === t.id ? "hg-btn-emerald" : "hg-btn-ghost"}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {msg && (
        <div
          style={{
            background: "#0d9488",
            color: "#fff",
            padding: "1rem 1.4rem",
            borderRadius: "14px",
            marginBottom: "1.5rem",
            fontWeight: 700,
          }}
        >
          {msg}
        </div>
      )}

      {/* TAB 1: QUẢN LÝ GÓI TẬP */}
      {tab === "plans" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={savePlan} className="card">
            <h3>{editingPlanId ? `✏️ Sửa Gói Tập #${editingPlanId}` : "➕ Thêm Gói Tập Mới"}</h3>
            <label style={{ fontSize: "0.85rem", fontWeight: 700, marginTop: "0.8rem" }}>Tên gói tập</label>
            <input
              className="input-box"
              value={planForm.name}
              onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })}
              required
            />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Số ngày sử dụng</label>
            <input
              type="number"
              className="input-box"
              value={planForm.duration_days}
              onChange={(e) => setPlanForm({ ...planForm, duration_days: Number(e.target.value) })}
              required
            />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Giá trọn gói (VNĐ)</label>
            <input
              type="number"
              className="input-box"
              value={planForm.price}
              onChange={(e) => setPlanForm({ ...planForm, price: Number(e.target.value) })}
              required
            />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Quyền lợi (cách nhau bằng dấu phẩy)</label>
            <textarea
              className="input-box"
              rows={3}
              value={planForm.benefits}
              onChange={(e) => setPlanForm({ ...planForm, benefits: e.target.value })}
            />
            <label style={{ display: "flex", gap: "0.5rem", marginBottom: "0.8rem", fontSize: "0.9rem" }}>
              <input
                type="checkbox"
                checked={planForm.is_popular}
                onChange={(e) => setPlanForm({ ...planForm, is_popular: e.target.checked })}
              />
              Đánh dấu là gói Phổ biến nhất
            </label>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button type="submit" className="hg-btn-emerald" style={{ flex: 1 }}>
                {editingPlanId ? "Lưu Cập Nhật" : "Thêm Gói Tập"}
              </button>
              {editingPlanId && (
                <button type="button" className="hg-btn-ghost" onClick={() => setEditingPlanId(null)}>
                  Hủy
                </button>
              )}
            </div>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Gói Tập ({plans.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tên gói</th>
                  <th>Thời hạn</th>
                  <th>Giá</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {plans.map((p) => (
                  <tr key={p.id}>
                    <td>#{p.id}</td>
                    <td><strong>{p.name}</strong></td>
                    <td>{p.duration_days} ngày</td>
                    <td style={{ color: "#0d9488", fontWeight: 700 }}>{formatCurrency(p.price)}</td>
                    <td style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingPlanId(p.id);
                          setPlanForm({
                            name: p.name,
                            duration_days: p.duration_days,
                            price: p.price,
                            benefits: p.benefits || "",
                            includes_pt: p.includes_pt,
                            is_popular: p.is_popular,
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.4rem 0.8rem" }}
                        onClick={() => deleteGymData(`/admin/plans/${p.id}`).then(() => notify("🗑️ Đã xóa gói tập"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: QUẢN LÝ LỚP HỌC */}
      {tab === "classes" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={saveClass} className="card">
            <h3>{editingClassId ? `✏️ Sửa Lớp Học #${editingClassId}` : "➕ Thêm Lớp Học Mới"}</h3>
            <label style={{ fontSize: "0.85rem", fontWeight: 700, marginTop: "0.8rem" }}>Tên lớp học</label>
            <input
              className="input-box"
              value={classForm.name}
              onChange={(e) => setClassForm({ ...classForm, name: e.target.value })}
              required
            />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Bộ môn</label>
            <select
              className="input-box"
              value={classForm.category}
              onChange={(e) => setClassForm({ ...classForm, category: e.target.value })}
            >
              <option value="Yoga">Yoga</option>
              <option value="HIIT">HIIT</option>
              <option value="Boxing">Boxing / Dance</option>
              <option value="Strength">Strength</option>
            </select>
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Lịch học</label>
            <input
              className="input-box"
              value={classForm.schedule_time}
              onChange={(e) => setClassForm({ ...classForm, schedule_time: e.target.value })}
              required
            />
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Phòng tập & Sức chứa</label>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <input
                className="input-box"
                placeholder="Phòng"
                value={classForm.room}
                onChange={(e) => setClassForm({ ...classForm, room: e.target.value })}
              />
              <input
                type="number"
                className="input-box"
                placeholder="Sức chứa"
                value={classForm.capacity}
                onChange={(e) => setClassForm({ ...classForm, capacity: Number(e.target.value) })}
              />
            </div>
            <button type="submit" className="hg-btn-emerald">
              {editingClassId ? "Lưu Cập Nhật" : "Thêm Lớp Học"}
            </button>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Lớp Học ({classes.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Tên lớp</th>
                  <th>Bộ môn</th>
                  <th>Lịch học</th>
                  <th>Sĩ số</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {classes.map((c) => (
                  <tr key={c.id}>
                    <td><strong>{c.name}</strong></td>
                    <td><span className="chip">{c.category}</span></td>
                    <td>{c.schedule_time}</td>
                    <td>{c.enrolled_count}/{c.capacity}</td>
                    <td style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingClassId(c.id);
                          setClassForm({
                            name: c.name,
                            category: c.category,
                            schedule_time: c.schedule_time,
                            room: c.room,
                            capacity: c.capacity,
                            description: c.description || "",
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.4rem 0.8rem" }}
                        onClick={() => deleteGymData(`/admin/classes/${c.id}`).then(() => notify("🗑️ Đã xóa lớp học"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: QUẢN LÝ HUẤN LUYỆN VIÊN */}
      {tab === "trainers" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={saveTrainer} className="card">
            <h3>{editingTrainerId ? `✏️ Sửa HLV #${editingTrainerId}` : "➕ Thêm Huấn Luyện Viên"}</h3>
            <input
              className="input-box"
              placeholder="Họ và tên HLV *"
              value={trainerForm.full_name}
              onChange={(e) => setTrainerForm({ ...trainerForm, full_name: e.target.value })}
              required
            />
            <input
              className="input-box"
              placeholder="Chuyên môn *"
              value={trainerForm.specialty}
              onChange={(e) => setTrainerForm({ ...trainerForm, specialty: e.target.value })}
              required
            />
            <input
              className="input-box"
              placeholder="Số điện thoại"
              value={trainerForm.phone}
              onChange={(e) => setTrainerForm({ ...trainerForm, phone: e.target.value })}
            />
            <input
              type="number"
              className="input-box"
              placeholder="Số năm kinh nghiệm"
              value={trainerForm.experience_years}
              onChange={(e) => setTrainerForm({ ...trainerForm, experience_years: Number(e.target.value) })}
            />
            <textarea
              className="input-box"
              rows={3}
              placeholder="Tiểu sử / Chứng chỉ"
              value={trainerForm.bio}
              onChange={(e) => setTrainerForm({ ...trainerForm, bio: e.target.value })}
            />
            <button type="submit" className="hg-btn-emerald">
              {editingTrainerId ? "Lưu Cập Nhật" : "Thêm HLV"}
            </button>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Huấn Luyện Viên ({trainers.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Họ tên</th>
                  <th>Chuyên môn</th>
                  <th>Kinh nghiệm</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {trainers.map((t) => (
                  <tr key={t.id}>
                    <td><strong>{t.full_name}</strong></td>
                    <td>{t.specialty}</td>
                    <td>{t.experience_years} năm</td>
                    <td style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingTrainerId(t.id);
                          setTrainerForm({
                            full_name: t.full_name,
                            specialty: t.specialty,
                            phone: t.phone || "",
                            experience_years: t.experience_years,
                            bio: t.bio || "",
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.4rem 0.8rem" }}
                        onClick={() => deleteGymData(`/admin/trainers/${t.id}`).then(() => notify("🗑️ Đã xóa HLV"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: QUẢN LÝ CHI NHÁNH */}
      {tab === "branches" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={saveBranch} className="card">
            <h3>{editingBranchId ? `✏️ Sửa Chi Nhánh #${editingBranchId}` : "➕ Thêm Chi Nhánh Mới"}</h3>
            <input
              className="input-box"
              placeholder="Tên chi nhánh *"
              value={branchForm.name}
              onChange={(e) => setBranchForm({ ...branchForm, name: e.target.value })}
              required
            />
            <input
              className="input-box"
              placeholder="Địa chỉ chi tiết *"
              value={branchForm.address}
              onChange={(e) => setBranchForm({ ...branchForm, address: e.target.value })}
              required
            />
            <input
              className="input-box"
              placeholder="Hotline"
              value={branchForm.phone}
              onChange={(e) => setBranchForm({ ...branchForm, phone: e.target.value })}
            />
            <input
              className="input-box"
              placeholder="Giờ mở cửa"
              value={branchForm.opening_hours}
              onChange={(e) => setBranchForm({ ...branchForm, opening_hours: e.target.value })}
            />
            <button type="submit" className="hg-btn-emerald">
              {editingBranchId ? "Lưu Cập Nhật" : "Thêm Chi Nhánh"}
            </button>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Chi Nhánh ({branches.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Tên chi nhánh</th>
                  <th>Địa chỉ</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {branches.map((b) => (
                  <tr key={b.id}>
                    <td><strong>{b.name}</strong></td>
                    <td>{b.address}</td>
                    <td style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingBranchId(b.id);
                          setBranchForm({
                            name: b.name,
                            address: b.address,
                            phone: b.phone || "",
                            opening_hours: b.opening_hours,
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.4rem 0.8rem" }}
                        onClick={() => deleteGymData(`/admin/branches/${b.id}`).then(() => notify("🗑️ Đã xóa chi nhánh"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: QUẢN LÝ THIẾT BỊ CSVC */}
      {tab === "facilities" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={saveFacility} className="card">
            <h3>{editingFacilityId ? `✏️ Sửa Thiết Bị #${editingFacilityId}` : "➕ Thêm Thiết Bị Mới"}</h3>
            <input
              className="input-box"
              placeholder="Tên thiết bị / khu vực *"
              value={facilityForm.name}
              onChange={(e) => setFacilityForm({ ...facilityForm, name: e.target.value })}
              required
            />
            <select
              className="input-box"
              value={facilityForm.category}
              onChange={(e) => setFacilityForm({ ...facilityForm, category: e.target.value })}
            >
              <option value="Cardio">Cardio</option>
              <option value="Strength">Strength (Tạ & Khung gánh)</option>
              <option value="Tiện ích">Tiện ích miễn phí</option>
            </select>
            <input
              type="number"
              className="input-box"
              placeholder="Số lượng"
              value={facilityForm.quantity}
              onChange={(e) => setFacilityForm({ ...facilityForm, quantity: Number(e.target.value) })}
            />
            <textarea
              className="input-box"
              rows={3}
              placeholder="Mô tả thiết bị"
              value={facilityForm.description}
              onChange={(e) => setFacilityForm({ ...facilityForm, description: e.target.value })}
            />
            <button type="submit" className="hg-btn-emerald">
              {editingFacilityId ? "Lưu Cập Nhật" : "Thêm Thiết Bị"}
            </button>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Thiết Bị ({facilities.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Tên thiết bị</th>
                  <th>Loại</th>
                  <th>Số lượng</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {facilities.map((f) => (
                  <tr key={f.id}>
                    <td><strong>{f.name}</strong></td>
                    <td><span className="chip">{f.category}</span></td>
                    <td>{f.quantity}</td>
                    <td style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingFacilityId(f.id);
                          setFacilityForm({
                            name: f.name,
                            category: f.category,
                            quantity: f.quantity,
                            status: f.status,
                            description: f.description || "",
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.4rem 0.8rem" }}
                        onClick={() => deleteGymData(`/admin/facilities/${f.id}`).then(() => notify("🗑️ Đã xóa thiết bị"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 6: QUẢN LÝ HỘI VIÊN */}
      {tab === "members" && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1.8fr" }}>
          <form onSubmit={saveMember} className="card">
            <h3>{editingMemberId ? `✏️ Sửa Hội Viên #${editingMemberId}` : "➕ Thêm Hội Viên"}</h3>
            <input
              className="input-box"
              placeholder="Họ và tên *"
              value={memberForm.full_name}
              onChange={(e) => setMemberForm({ ...memberForm, full_name: e.target.value })}
              required
            />
            <input
              className="input-box"
              placeholder="Số điện thoại"
              value={memberForm.phone}
              onChange={(e) => setMemberForm({ ...memberForm, phone: e.target.value })}
            />
            <select
              className="input-box"
              value={memberForm.status}
              onChange={(e) => setMemberForm({ ...memberForm, status: e.target.value })}
            >
              <option value="active">active (Đang hoạt động)</option>
              <option value="frozen">frozen (Đang bảo lưu)</option>
              <option value="expired">expired (Đã hết hạn)</option>
              <option value="inactive">inactive (Chưa kích hoạt)</option>
            </select>
            <label style={{ fontSize: "0.85rem", fontWeight: 700 }}>Hạn thẻ (YYYY-MM-DD)</label>
            <input
              type="date"
              className="input-box"
              value={memberForm.expire_date}
              onChange={(e) => setMemberForm({ ...memberForm, expire_date: e.target.value })}
            />
            <button type="submit" className="hg-btn-emerald">
              {editingMemberId ? "Lưu Cập Nhật" : "Thêm Hội Viên"}
            </button>
          </form>

          <div className="table-wrap">
            <h3>Danh Sách Hội Viên ({members.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>Họ tên</th>
                  <th>SĐT</th>
                  <th>Trạng thái</th>
                  <th>Hạn thẻ</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id}>
                    <td><strong>{m.full_name}</strong></td>
                    <td>{m.phone || "—"}</td>
                    <td><span className="chip">{m.status}</span></td>
                    <td>{m.expire_date || "—"}</td>
                    <td style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                      <button
                        className="hg-btn-emerald"
                        style={{ padding: "0.35rem 0.7rem", fontSize: "0.8rem" }}
                        onClick={() => postGymData(`/interactions/checkin/${m.id}`).then((r) => notify(r.message)).catch((e) => notify(e.message))}
                      >
                        Check-in
                      </button>
                      <button
                        className="hg-btn-ghost"
                        onClick={() => {
                          setEditingMemberId(m.id);
                          setMemberForm({
                            full_name: m.full_name,
                            phone: m.phone || "",
                            email: m.email || "",
                            status: m.status,
                            expire_date: m.expire_date || "",
                          });
                        }}
                      >
                        Sửa
                      </button>
                      <button
                        className="hg-btn-coral"
                        style={{ padding: "0.35rem 0.7rem", fontSize: "0.8rem" }}
                        onClick={() => deleteGymData(`/admin/members/${m.id}`).then(() => notify("🗑️ Đã xóa hội viên"))}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
"""
}

def main():
    for filepath, content in FILES.items():
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    print("✅ Đã tách riêng từng trang + Tạo trang Quản trị Admin Full CRUD + Giao diện Fresh Mint & Coral Wellness!")

if __name__ == "__main__":
    main()