"""Migration nhẹ cho các cột mới thêm vào bảng đã tồn tại.

`Base.metadata.create_all()` chỉ tạo BẢNG MỚI, không thêm cột vào bảng đã có.
Với các bản cài đặt HealthyGym đã tồn tại từ trước, module này bổ sung những
cột mới (phân hệ AI, PT 1-1, HLV) mà không cần công cụ migration bên ngoài.

Mọi câu lệnh đều dùng IF NOT EXISTS nên chạy lại nhiều lần vẫn an toàn
(idempotent). Hỗ trợ cả PostgreSQL và SQLite.
"""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("healthygym.migrations")

#: (bảng, cột, định nghĩa kiểu) cần bổ sung nếu chưa tồn tại
COLUMN_MIGRATIONS: list[tuple[str, str, str]] = [
    # --- Hội viên: gắn HLV phụ trách ---
    ("members", "trainer_id", "INTEGER REFERENCES trainers(id)"),
    # --- HLV: hồ sơ mở rộng cho dashboard ---
    ("trainers", "rating", "DOUBLE PRECISION DEFAULT 5.0"),
    ("trainers", "certifications", "TEXT"),
    ("trainers", "user_id", "INTEGER REFERENCES users(id)"),

    # ======================================================================
    # MỞ RỘNG ERP v3 — các cột thêm vào bảng đã tồn tại
    # ======================================================================
    # --- Hội viên: phân hạng thẻ, điểm thưởng, công nợ, CRM ---
    ("members", "tier", "VARCHAR(20) DEFAULT 'standard'"),
    ("members", "time_window", "VARCHAR(20) DEFAULT 'full_time'"),
    ("members", "home_branch_id", "INTEGER REFERENCES branches(id)"),
    ("members", "has_private_locker", "BOOLEAN DEFAULT FALSE"),
    ("members", "loyalty_points", "INTEGER DEFAULT 0"),
    ("members", "total_points_earned", "INTEGER DEFAULT 0"),
    ("members", "outstanding_debt", "DOUBLE PRECISION DEFAULT 0"),
    ("members", "is_debt_blocked", "BOOLEAN DEFAULT FALSE"),
    ("members", "qr_code", "VARCHAR(60)"),
    ("members", "last_visit_date", "DATE"),
    ("members", "risk_level", "VARCHAR(20) DEFAULT 'low'"),
    ("members", "referred_by_member_id", "INTEGER REFERENCES members(id)"),
    ("members", "emergency_contact", "VARCHAR(255)"),
    ("members", "date_of_birth", "DATE"),
    ("members", "gender", "VARCHAR(10) DEFAULT 'male'"),
    ("members", "note", "TEXT"),

    # --- HLV: thù lao & chuyên môn ---
    ("trainers", "email", "VARCHAR(255)"),
    ("trainers", "rating_count", "INTEGER DEFAULT 0"),
    ("trainers", "is_active", "BOOLEAN DEFAULT TRUE"),
    ("trainers", "base_salary", "DOUBLE PRECISION DEFAULT 6000000"),
    ("trainers", "burn_fee_per_session", "DOUBLE PRECISION DEFAULT 80000"),
    ("trainers", "sale_commission_rate", "DOUBLE PRECISION DEFAULT 0.10"),
    ("trainers", "accepts_rehab", "BOOLEAN DEFAULT FALSE"),
    ("trainers", "max_trainees", "INTEGER DEFAULT 20"),
    ("trainers", "current_trainees", "INTEGER DEFAULT 0"),

    # --- Người dùng: theo dõi đăng nhập ---
    ("users", "last_login_at", "TIMESTAMP"),

    # --- Gói tập: cấu hình hạng thẻ & quy tắc nghiệp vụ ---
    ("membership_plans", "plan_kind", "VARCHAR(20) DEFAULT 'membership'"),
    ("membership_plans", "tier", "VARCHAR(20) DEFAULT 'standard'"),
    ("membership_plans", "time_window", "VARCHAR(20) DEFAULT 'full_time'"),
    ("membership_plans", "off_peak_start_hour", "INTEGER DEFAULT 9"),
    ("membership_plans", "off_peak_end_hour", "INTEGER DEFAULT 16"),
    ("membership_plans", "branch_scope", "VARCHAR(20) DEFAULT 'single'"),
    ("membership_plans", "includes_locker", "BOOLEAN DEFAULT FALSE"),
    ("membership_plans", "includes_towel", "BOOLEAN DEFAULT TRUE"),
    ("membership_plans", "includes_sauna", "BOOLEAN DEFAULT FALSE"),
    ("membership_plans", "guest_passes_month", "INTEGER DEFAULT 0"),
    ("membership_plans", "freeze_allowed", "BOOLEAN DEFAULT TRUE"),
    ("membership_plans", "max_freeze_days", "INTEGER DEFAULT 60"),
    ("membership_plans", "min_freeze_days", "INTEGER DEFAULT 7"),
    ("membership_plans", "min_duration_for_freeze", "INTEGER DEFAULT 90"),
    ("membership_plans", "transfer_allowed", "BOOLEAN DEFAULT TRUE"),
    ("membership_plans", "transfer_fee", "DOUBLE PRECISION DEFAULT 300000"),
    ("membership_plans", "min_days_for_transfer", "INTEGER DEFAULT 30"),
    ("membership_plans", "included_pt_sessions", "INTEGER DEFAULT 0"),
    ("membership_plans", "min_commitment_months", "INTEGER DEFAULT 1"),

    # --- Thiết bị: vòng đời & bảo trì định kỳ ---
    ("facilities", "lifecycle_status", "VARCHAR(20) DEFAULT 'active'"),
    ("facilities", "brand", "VARCHAR(100)"),
    ("facilities", "model", "VARCHAR(100)"),
    ("facilities", "serial_number", "VARCHAR(100)"),
    ("facilities", "purchase_date", "DATE"),
    ("facilities", "warranty_until", "DATE"),
    ("facilities", "maintenance_cycle_days", "INTEGER DEFAULT 90"),
    ("facilities", "last_maintenance_date", "DATE"),
    ("facilities", "next_maintenance_date", "DATE"),
    ("facilities", "location_note", "VARCHAR(255)"),

    # --- Lịch lớp GroupX: phòng, độ khó, chọn vị trí ---
    ("gym_classes", "difficulty", "VARCHAR(20) DEFAULT 'intermediate'"),
    ("gym_classes", "requires_spot_selection", "BOOLEAN DEFAULT FALSE"),
    ("gym_classes", "duration_minutes", "INTEGER DEFAULT 60"),
]


def _supports_if_not_exists(engine: Engine) -> bool:
    """PostgreSQL hỗ trợ ADD COLUMN IF NOT EXISTS; SQLite thì không."""
    return engine.dialect.name == "postgresql"


def run_lightweight_migrations(engine: Engine) -> list[str]:
    """Thêm các cột còn thiếu. Trả về danh sách cột đã thêm."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    applied: list[str] = []

    # Cache cột hiện có của từng bảng để tránh query lặp lại
    columns_cache: dict[str, set[str]] = {}

    def columns_of(table: str) -> set[str]:
        if table not in columns_cache:
            columns_cache[table] = {c["name"] for c in inspector.get_columns(table)}
        return columns_cache[table]

    with engine.begin() as conn:
        for table, column, definition in COLUMN_MIGRATIONS:
            if table not in existing_tables:
                continue  # bảng chưa tồn tại -> create_all sẽ tạo đủ cột
            if column in columns_of(table):
                continue

            if _supports_if_not_exists(engine):
                sql = f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{column}" {definition}'
            else:
                sql = f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}'

            try:
                conn.execute(text(sql))
                columns_cache[table].add(column)
                applied.append(f"{table}.{column}")
                logger.info("Đã thêm cột %s.%s", table, column)
            except Exception as exc:  # pragma: no cover - phụ thuộc DB cụ thể
                logger.warning("Không thể thêm cột %s.%s: %s", table, column, exc)

    if applied:
        logger.info("Migration hoàn tất, đã thêm: %s", ", ".join(applied))
    return applied