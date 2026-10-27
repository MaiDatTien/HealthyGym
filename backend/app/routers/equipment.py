"""Router THIẾT BỊ & BẢO TRÌ — mã QR trên từng máy, vòng đời bảo trì,
và liên kết thông minh với AI Coach (tự loại bài tập khi máy hỏng).
"""
from __future__ import annotations

import secrets
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.engagement import MachineQR
from app.models.interaction import now_local
from app.models.listing import Branch, Facility
from app.models.pt import EquipmentMaintenance
from app.models.user import User
from app.schemas.erp import (
    EquipmentReport, MachineQRCreate, MaintenanceSchedule,
)
from app.security import (
    get_current_user, get_optional_user, require_facility_manager,
    require_operations,
)

router = APIRouter(prefix="/equipment", tags=["Equipment & Maintenance"])


class LifecycleStatus:
    """Vòng đời thiết bị."""

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    OUT_OF_ORDER = "out_of_order"

    LABELS = {
        ACTIVE: "Đang hoạt động tốt",
        MAINTENANCE: "Đang bảo trì",
        OUT_OF_ORDER: "Ngưng sử dụng",
    }


def _sync_lifecycle_from_tickets(facility: Facility, db: Session) -> None:
    """Đồng bộ trạng thái thiết bị từ các phiếu bảo trì đang mở."""
    open_tickets = (
        db.query(EquipmentMaintenance)
        .filter(
            EquipmentMaintenance.facility_id == facility.id,
            EquipmentMaintenance.status != "resolved",
        )
        .all()
    )

    if not open_tickets:
        facility.lifecycle_status = LifecycleStatus.ACTIVE
        facility.status = "Hoạt động tốt"
        return

    if any(t.severity == "high" for t in open_tickets):
        facility.lifecycle_status = LifecycleStatus.OUT_OF_ORDER
        facility.status = "Ngưng sử dụng"
    else:
        facility.lifecycle_status = LifecycleStatus.MAINTENANCE
        facility.status = "Đang bảo trì"


# ==========================================================================
# DANH MỤC THIẾT BỊ
# ==========================================================================
@router.get("/list")
def list_equipment(
    branch_id: Optional[int] = None,
    category: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Danh mục thiết bị kèm trạng thái vòng đời và lịch bảo trì."""
    query = db.query(Facility)
    if branch_id:
        query = query.filter(Facility.branch_id == branch_id)
    if category:
        query = query.filter(Facility.category == category)
    if lifecycle_status:
        query = query.filter(Facility.lifecycle_status == lifecycle_status)

    facilities = query.order_by(Facility.id.asc()).all()
    today = date.today()

    result = []
    for f in facilities:
        open_tickets = (
            db.query(func.count(EquipmentMaintenance.id))
            .filter(
                EquipmentMaintenance.facility_id == f.id,
                EquipmentMaintenance.status != "resolved",
            )
            .scalar()
            or 0
        )
        days_to_maintenance = (
            (f.next_maintenance_date - today).days if f.next_maintenance_date else None
        )

        result.append({
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "quantity": f.quantity,
            "brand": f.brand,
            "model": f.model,
            "branch_id": f.branch_id,
            "lifecycle_status": f.lifecycle_status,
            "lifecycle_label": LifecycleStatus.LABELS.get(
                f.lifecycle_status or LifecycleStatus.ACTIVE, "?"
            ),
            "display_status": f.status,
            "open_maintenance_tickets": open_tickets,
            "last_maintenance_date": f.last_maintenance_date,
            "next_maintenance_date": f.next_maintenance_date,
            "maintenance_cycle_days": f.maintenance_cycle_days,
            "days_to_maintenance": days_to_maintenance,
            "maintenance_due": (
                days_to_maintenance is not None and days_to_maintenance <= 0
            ),
            "maintenance_warning": (
                f"⚠️ Quá hạn bảo trì {abs(days_to_maintenance)} ngày!"
                if days_to_maintenance is not None and days_to_maintenance < 0
                else (
                    f"⏰ Đến hạn bảo trì trong {days_to_maintenance} ngày"
                    if days_to_maintenance is not None and days_to_maintenance <= 14
                    else None
                )
            ),
            "is_usable": f.lifecycle_status == LifecycleStatus.ACTIVE,
        })
    return result


@router.get("/{facility_id}")
def equipment_detail(facility_id: int, db: Session = Depends(get_db)):
    """Chi tiết thiết bị kèm lịch sử bảo trì và mã QR."""
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    tickets = (
        db.query(EquipmentMaintenance)
        .filter(EquipmentMaintenance.facility_id == facility_id)
        .order_by(EquipmentMaintenance.reported_at.desc())
        .limit(30)
        .all()
    )
    qrs = db.query(MachineQR).filter(MachineQR.facility_id == facility_id).all()

    total_cost = sum(t.cost or 0 for t in tickets)

    return {
        "id": facility.id,
        "name": facility.name,
        "category": facility.category,
        "quantity": facility.quantity,
        "brand": facility.brand,
        "model": facility.model,
        "serial_number": facility.serial_number,
        "purchase_date": facility.purchase_date,
        "warranty_until": facility.warranty_until,
        "lifecycle_status": facility.lifecycle_status,
        "lifecycle_label": LifecycleStatus.LABELS.get(
            facility.lifecycle_status or LifecycleStatus.ACTIVE, "?"
        ),
        "maintenance_cycle_days": facility.maintenance_cycle_days,
        "last_maintenance_date": facility.last_maintenance_date,
        "next_maintenance_date": facility.next_maintenance_date,
        "total_maintenance_cost": total_cost,
        "maintenance_count": len(tickets),
        "machine_qrs": [
            {
                "qr_code": q.qr_code,
                "machine_code": q.machine_code,
                "display_name": q.display_name,
                "exercise_name": q.exercise_name,
                "video_url": q.video_url,
            }
            for q in qrs
        ],
        "maintenance_history": [
            {
                "id": t.id,
                "issue": t.issue,
                "severity": t.severity,
                "status": t.status,
                "technician": t.technician,
                "cost": t.cost,
                "reported_by": t.reported_by,
                "reported_at": t.reported_at,
                "resolved_at": t.resolved_at,
            }
            for t in tickets
        ],
    }


# ==========================================================================
# MÃ QR TRÊN TỪNG MÁY — HƯỚNG DẪN SỬ DỤNG
# ==========================================================================
@router.post("/machine-qr")
def create_machine_qr(
    data: MachineQRCreate,
    current_user: User = Depends(require_facility_manager),
    db: Session = Depends(get_db),
):
    """Tạo mã QR cho một máy tập cụ thể."""
    facility = db.query(Facility).filter(Facility.id == data.facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    exists = (
        db.query(MachineQR)
        .filter(MachineQR.machine_code == data.machine_code)
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=400, detail=f"Mã máy '{data.machine_code}' đã tồn tại"
        )

    qr = MachineQR(
        facility_id=data.facility_id,
        qr_code=f"MQ-{data.machine_code}-{secrets.token_hex(3).upper()}",
        machine_code=data.machine_code,
        display_name=data.display_name,
        video_url=data.video_url,
        setup_guide=data.setup_guide,
        posture_guide=data.posture_guide,
        common_mistakes=data.common_mistakes,
        target_muscles=data.target_muscles,
        difficulty=data.difficulty,
        exercise_name=data.exercise_name,
    )
    db.add(qr)
    db.commit()
    db.refresh(qr)

    return {
        "message": f"Đã tạo mã QR cho '{qr.display_name}' ({qr.machine_code})",
        "qr_code": qr.qr_code,
        "machine_code": qr.machine_code,
        "print_note": (
            f"In mã QR '{qr.qr_code}' và dán lên thân máy. Hội viên quét mã sẽ xem được "
            f"hướng dẫn sử dụng và có thể báo hỏng ngay."
        ),
    }


@router.get("/scan/{qr_code}")
def scan_machine_qr(
    qr_code: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Hội viên quét mã QR trên máy — xem hướng dẫn sử dụng và tình trạng máy."""
    qr = db.query(MachineQR).filter(MachineQR.qr_code == qr_code.strip()).first()
    if not qr:
        raise HTTPException(status_code=404, detail="Mã QR không hợp lệ hoặc không tồn tại")

    facility = qr.facility
    open_tickets = (
        db.query(func.count(EquipmentMaintenance.id))
        .filter(
            EquipmentMaintenance.facility_id == qr.facility_id,
            EquipmentMaintenance.status != "resolved",
        )
        .scalar()
        or 0
    ) if facility else 0

    is_usable = facility.lifecycle_status == LifecycleStatus.ACTIVE if facility else True

    return {
        "machine_code": qr.machine_code,
        "display_name": qr.display_name,
        "facility_name": facility.name if facility else None,
        "category": facility.category if facility else None,
        "brand": facility.brand if facility else None,
        "model": facility.model if facility else None,
        "lifecycle_status": facility.lifecycle_status if facility else None,
        "is_usable": is_usable,
        "status_warning": (
            None if is_usable else
            f"⚠️ Máy này đang ở trạng thái '"
            f"{LifecycleStatus.LABELS.get(facility.lifecycle_status, '?')}'. "
            f"Vui lòng chọn máy khác hoặc báo lễ tân."
        ),
        "open_tickets": open_tickets,
        # --- Hướng dẫn sử dụng ---
        "video_url": qr.video_url,
        "setup_guide": qr.setup_guide,
        "posture_guide": qr.posture_guide,
        "common_mistakes": qr.common_mistakes,
        "target_muscles": qr.target_muscles,
        "difficulty": qr.difficulty,
        "linked_exercise": qr.exercise_name,
        # --- Gợi ý ---
        "ai_tip": (
            f"Bài tập này tác động chính vào {qr.target_muscles}. "
            f"Hãy khởi động kỹ nhóm cơ này trước khi tập và bắt đầu với mức tạ nhẹ "
            f"để làm quen chuyển động."
            if qr.target_muscles else
            "Hãy khởi động kỹ trước khi tập và bắt đầu với mức tạ nhẹ."
        ),
        "can_report_issue": True,
        "report_hint": (
            "Nếu phát hiện máy hỏng (đứt cáp, rách đệm, kẹt tạ...), hãy bấm 'Báo hỏng' "
            "để kỹ thuật viên xử lý kịp thời."
        ),
    }


# ==========================================================================
# BÁO HỎNG & BẢO TRÌ
# ==========================================================================
@router.post("/report-issue")
def report_equipment_issue(
    data: EquipmentReport,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hội viên hoặc PT báo hỏng thiết bị ngay trên web."""
    facility = db.query(Facility).filter(Facility.id == data.facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    machine_label = facility.name
    if data.machine_qr_code:
        qr = (
            db.query(MachineQR)
            .filter(MachineQR.qr_code == data.machine_qr_code.strip())
            .first()
        )
        if qr:
            machine_label = f"{qr.display_name} ({qr.machine_code})"

    ticket = EquipmentMaintenance(
        facility_id=data.facility_id,
        issue=f"[{machine_label}] {data.issue}",
        severity=data.severity,
        status="pending",
        reported_by=current_user.full_name or current_user.username,
    )
    db.add(ticket)
    db.flush()

    _sync_lifecycle_from_tickets(facility, db)

    db.commit()
    db.refresh(ticket)

    severity_msg = {
        "high": "🔴 Mức độ NGHIÊM TRỌNG — thiết bị đã được chuyển sang trạng thái "
                "'Ngưng sử dụng' và AI Coach sẽ tạm không xếp bài tập này.",
        "medium": "🟠 Mức độ TRUNG BÌNH — thiết bị chuyển sang 'Đang bảo trì', "
                  "kỹ thuật viên sẽ kiểm tra trong 24 giờ.",
        "low": "🟡 Mức độ THẤP — phiếu đã được ghi nhận cho lần bảo trì định kỳ tới.",
    }

    return {
        "message": f"Cảm ơn bạn đã báo hỏng! Phiếu bảo trì #{ticket.id} đã được tạo.",
        "ticket_id": ticket.id,
        "severity": data.severity,
        "severity_note": severity_msg.get(data.severity, ""),
        "facility_status": facility.lifecycle_status,
        "facility_status_label": LifecycleStatus.LABELS.get(
            facility.lifecycle_status, "?"
        ),
        "ai_coach_sync": (
            "AI Coach đã được cập nhật: bài tập dùng thiết bị này sẽ tự động được "
            "thay bằng bài tương đương cho các hội viên tập tại chi nhánh này."
            if facility.lifecycle_status != LifecycleStatus.ACTIVE else None
        ),
    }


@router.post("/maintenance")
def create_maintenance_ticket(
    data: EquipmentReport,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Nhân sự tạo phiếu bảo trì (dùng cho cả bảo trì định kỳ)."""
    return report_equipment_issue(data, current_user, db)


@router.get("/maintenance/tickets")
def list_maintenance_tickets(
    status: Optional[str] = Query(None, pattern="^(pending|in_progress|resolved)$"),
    severity: Optional[str] = Query(None, pattern="^(low|medium|high)$"),
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Danh sách phiếu bảo trì."""
    query = db.query(EquipmentMaintenance)
    if status:
        query = query.filter(EquipmentMaintenance.status == status)
    if severity:
        query = query.filter(EquipmentMaintenance.severity == severity)

    tickets = query.order_by(EquipmentMaintenance.reported_at.desc()).limit(200).all()

    pending = db.query(func.count(EquipmentMaintenance.id)).filter(
        EquipmentMaintenance.status == "pending"
    ).scalar() or 0
    in_progress = db.query(func.count(EquipmentMaintenance.id)).filter(
        EquipmentMaintenance.status == "in_progress"
    ).scalar() or 0

    return {
        "total": len(tickets),
        "pending": pending,
        "in_progress": in_progress,
        "tickets": [
            {
                "id": t.id,
                "facility_id": t.facility_id,
                "facility_name": t.facility.name if t.facility else None,
                "branch_id": t.facility.branch_id if t.facility else None,
                "issue": t.issue,
                "severity": t.severity,
                "status": t.status,
                "reported_by": t.reported_by,
                "technician": t.technician,
                "cost": t.cost,
                "reported_at": t.reported_at,
                "resolved_at": t.resolved_at,
                "days_open": (date.today() - t.reported_at.date()).days
                if t.reported_at else 0,
            }
            for t in tickets
        ],
    }


@router.put("/maintenance/{ticket_id}")
def update_maintenance_ticket(
    ticket_id: int,
    status: str = Query(..., pattern="^(pending|in_progress|resolved)$"),
    technician: Optional[str] = None,
    cost: Optional[float] = None,
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Cập nhật trạng thái phiếu bảo trì."""
    ticket = (
        db.query(EquipmentMaintenance)
        .filter(EquipmentMaintenance.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu bảo trì")

    ticket.status = status
    if technician:
        ticket.technician = technician
    if cost is not None:
        ticket.cost = cost

    facility = db.query(Facility).filter(Facility.id == ticket.facility_id).first()

    if status == "resolved":
        ticket.resolved_at = now_local()
        # Cập nhật lịch bảo trì định kỳ
        if facility:
            facility.last_maintenance_date = date.today()
            cycle = facility.maintenance_cycle_days or 90
            facility.next_maintenance_date = date.today() + timedelta(days=cycle)

    if facility:
        _sync_lifecycle_from_tickets(facility, db)

    db.commit()

    return {
        "message": (
            f"Đã cập nhật phiếu #{ticket.id} sang '{status}'."
            + (
                f" Thiết bị '{facility.name}' đã trở lại trạng thái hoạt động."
                if facility and facility.lifecycle_status == LifecycleStatus.ACTIVE
                else ""
            )
        ),
        "ticket_id": ticket.id,
        "status": ticket.status,
        "facility_lifecycle_status": facility.lifecycle_status if facility else None,
    }


@router.post("/maintenance/schedule")
def set_maintenance_schedule(
    data: MaintenanceSchedule,
    current_user: User = Depends(require_facility_manager),
    db: Session = Depends(get_db),
):
    """Đặt lịch bảo trì định kỳ cho thiết bị."""
    facility = db.query(Facility).filter(Facility.id == data.facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    facility.maintenance_cycle_days = data.maintenance_cycle_days
    facility.next_maintenance_date = data.next_maintenance_date or (
        date.today() + timedelta(days=data.maintenance_cycle_days)
    )

    # Tạo phiếu bảo trì định kỳ nếu chưa có
    existing = (
        db.query(EquipmentMaintenance)
        .filter(
            EquipmentMaintenance.facility_id == facility.id,
            EquipmentMaintenance.status != "resolved",
            EquipmentMaintenance.issue.like("%định kỳ%"),
        )
        .first()
    )

    if not existing:
        db.add(EquipmentMaintenance(
            facility_id=facility.id,
            issue=(
                f"Bảo trì định kỳ mỗi {data.maintenance_cycle_days} ngày "
                f"({data.note or 'Kiểm tra tổng thể, tra dầu, siết ốc, kiểm tra cáp'})"
            ),
            severity="low",
            status="pending",
            reported_by=current_user.full_name or current_user.username,
            technician=None,
        ))

    db.commit()

    return {
        "message": (
            f"Đã đặt lịch bảo trì định kỳ mỗi {data.maintenance_cycle_days} ngày cho "
            f"'{facility.name}'. Lần bảo trì tới: {facility.next_maintenance_date}."
        ),
        "facility_id": facility.id,
        "cycle_days": facility.maintenance_cycle_days,
        "next_maintenance_date": facility.next_maintenance_date,
    }


@router.get("/maintenance/upcoming")
def upcoming_maintenance(
    days_ahead: int = Query(30, ge=1, le=180),
    current_user: User = Depends(require_operations),
    db: Session = Depends(get_db),
):
    """Thiết bị đến hạn bảo trì trong N ngày tới."""
    today = date.today()
    until = today + timedelta(days=days_ahead)

    facilities = (
        db.query(Facility)
        .filter(
            Facility.next_maintenance_date != None,
            Facility.next_maintenance_date <= until,
        )
        .order_by(Facility.next_maintenance_date.asc())
        .all()
    )

    overdue = [f for f in facilities if f.next_maintenance_date < today]
    upcoming = [f for f in facilities if f.next_maintenance_date >= today]

    return {
        "overdue_count": len(overdue),
        "upcoming_count": len(upcoming),
        "overdue": [
            {
                "facility_id": f.id,
                "name": f.name,
                "category": f.category,
                "next_maintenance_date": f.next_maintenance_date,
                "days_overdue": (today - f.next_maintenance_date).days,
                "lifecycle_status": f.lifecycle_status,
            }
            for f in overdue
        ],
        "upcoming": [
            {
                "facility_id": f.id,
                "name": f.name,
                "category": f.category,
                "next_maintenance_date": f.next_maintenance_date,
                "days_until": (f.next_maintenance_date - today).days,
                "lifecycle_status": f.lifecycle_status,
            }
            for f in upcoming
        ],
        "advice": (
            f"Có {len(overdue)} thiết bị QUÁ HẠN bảo trì. Nên xử lý ngay để tránh "
            f"hỏng nặng và gián đoạn dịch vụ."
            if overdue else
            f"Có {len(upcoming)} thiết bị đến hạn bảo trì trong {days_ahead} ngày tới."
        ),
    }


# ==========================================================================
# LIÊN KẾT THÔNG MINH VỚI AI COACH
# ==========================================================================
@router.get("/ai-coach/unavailable")
def unavailable_for_ai_coach(
    branch_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """Danh sách thiết bị KHÔNG khả dụng — AI Coach dùng để loại bài tập.

    Khi máy Leg Press đang 'Đang bảo trì', AI Coach tự biết và tạm thời không xếp
    bài Leg Press vào lịch tập hôm đó cho hội viên tập tại chi nhánh này.
    """
    query = db.query(Facility).filter(
        Facility.lifecycle_status.in_(
            [LifecycleStatus.MAINTENANCE, LifecycleStatus.OUT_OF_ORDER]
        )
    )
    if branch_id:
        query = query.filter(Facility.branch_id == branch_id)

    facilities = query.all()

    # Gom nhóm theo bài tập bị ảnh hưởng
    blocked_exercises: set[str] = set()
    details: list[dict] = []

    for f in facilities:
        affected = (
            db.query(MachineQR)
            .filter(
                MachineQR.facility_id == f.id,
                MachineQR.exercise_name != None,
            )
            .all()
        )
        # Hạ tầng chung (khu tạ, cardio) ảnh hưởng theo category
        category_map = {
            "Cardio": ["Máy chạy bộ", "Xe đạp", "Elliptical", "Máy chèo thuyền"],
            "Strength": ["Leg Press", "Cable", "Smith Machine", "Lat Pulldown"],
        }
        category_exercises = category_map.get(f.category, [])

        for q in affected:
            if q.exercise_name:
                blocked_exercises.add(q.exercise_name)

        details.append({
            "facility_id": f.id,
            "name": f.name,
            "category": f.category,
            "lifecycle_status": f.lifecycle_status,
            "lifecycle_label": LifecycleStatus.LABELS.get(f.lifecycle_status, "?"),
            "affected_exercises": [q.exercise_name for q in affected if q.exercise_name]
            or category_exercises,
            "quantity_affected": f.quantity,
        })

    return {
        "unavailable_count": len(facilities),
        "blocked_exercise_names": sorted(blocked_exercises),
        "details": details,
        "ai_coach_behavior": (
            "AI Coach sẽ tự động loại các bài tập này khỏi lịch tập của hội viên tại "
            "chi nhánh tương ứng, và gợi ý bài thay thế cùng nhóm cơ tác động "
            "(qua chức năng 'Đổi bài tập tức thì')."
        ),
        "note": (
            "Danh sách này được cập nhật tự động mỗi khi có phiếu bảo trì mới hoặc "
            "khi thiết bị được sửa xong."
        )
        if facilities else "Tất cả thiết bị đang hoạt động tốt — không có bài tập nào bị chặn.",
    }