"""Dữ liệu mẫu cho 7 phân hệ ERP mới (v3).

Tách riêng khỏi seed_data.py để giữ file gốc gọn, và để dễ bật/tắt dữ liệu demo.
Mọi hàm đều idempotent — chạy lại nhiều lần vẫn an toàn.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.ai import PARQScreening
from app.models.engagement import Badge, Challenge, MachineQR, MemberStreak, Reward
from app.models.interaction import now_local
from app.models.listing import Branch, Facility, GymClass, MembershipPlan
from app.models.membership import (
    ContractStatus, Installment, Lead, LeadStage, MemberWallet,
    MembershipContract, PaymentStatus, TierLevel, TimeWindow,
)
from app.models.operations import ClassSchedule, Locker, Product, ScheduleStatus
from app.models.trainer_ops import PTPackage, TrainerShift
from app.models.user import Trainer, User
from app.security import get_password_hash


#: Danh sách 6 tài khoản demo cho 6 vai trò RBAC
DEMO_ACCOUNTS: list[tuple[str, str, str]] = [
    ("admin", "Quản trị viên Hệ thống (Owner)", "admin"),
    ("letan", "Lễ tân & Tư vấn Nguyễn Hoàng", "receptionist"),
    ("csvc", "Quản lý CSVC Trần Văn Khoa", "facility_manager"),
    ("hlv", "HLV Trần Quốc Tuấn", "trainer"),
    ("hoivien", "Mai Tiến Đạt", "member"),
    # Tài khoản cũ, giữ lại để tương thích ngược — vai trò đã chuẩn hoá
    ("staff", "Lễ tân Nguyễn Hoàng (tài khoản cũ)", "receptionist"),
]


def ensure_role_accounts(db: Session) -> None:
    """Đảm bảo đủ tài khoản demo cho 6 vai trò RBAC."""
    for username, full_name, role in DEMO_ACCOUNTS:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            db.add(User(
                username=username,
                email=f"{username}@healthygym.vn",
                full_name=full_name,
                hashed_password=get_password_hash("123"),
                role=role,
                is_active=True,
            ))
        else:
            # Chuẩn hoá vai trò cũ 'staff' -> 'receptionist'
            if user.role != role:
                user.role = role
            user.hashed_password = get_password_hash("123")
            user.is_active = True
    db.commit()


def seed_contracts(db: Session, member) -> None:
    """Hợp đồng hội viên + ví + streak."""
    if db.query(MembershipContract).count() > 0:
        return

    today = date.today()
    plan = (
        db.query(MembershipPlan).filter(MembershipPlan.duration_days == 180).first()
        or db.query(MembershipPlan).first()
    )
    if not plan or not member:
        return

    contract = MembershipContract(
        contract_code=f"HD-{today.strftime('%Y%m')}-0001",
        member_id=member.id,
        plan_id=plan.id,
        branch_id=member.home_branch_id,
        tier=TierLevel.GOLD,
        time_window=TimeWindow.FULL_TIME,
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=170),
        duration_days=180,
        list_price=plan.price,
        final_price=plan.price,
        paid_amount=plan.price,
        payment_status=PaymentStatus.PAID,
        status=ContractStatus.ACTIVE,
        includes_locker=False,
        includes_towel=True,
        includes_sauna=True,
        guest_passes_month=2,
        sold_by="Lễ tân Nguyễn Hoàng",
    )
    db.add(contract)
    db.flush()

    db.add(Installment(
        contract_id=contract.id, member_id=member.id, sequence=1,
        amount=plan.price, due_date=contract.start_date,
        paid_amount=plan.price, paid_at=now_local(),
        status=PaymentStatus.PAID, method="Chuyển khoản QR",
        note="Thanh toán một lần",
    ))

    # Đồng bộ hồ sơ hội viên
    member.tier = TierLevel.GOLD
    member.time_window = TimeWindow.FULL_TIME
    member.current_plan_id = plan.id
    member.expire_date = contract.end_date
    member.status = "active"
    member.loyalty_points = 480
    member.total_points_earned = 480
    member.last_visit_date = today - timedelta(days=1)
    member.join_date = contract.start_date

    db.add(MemberWallet(
        member_id=member.id, balance=250000, total_topup=500000, total_spent=250000,
    ))
    db.add(MemberStreak(
        member_id=member.id,
        current_week_streak=6, longest_week_streak=6,
        current_day_streak=2, longest_day_streak=5,
        last_activity_date=today - timedelta(days=1),
        total_checkins=18, total_workouts_logged=14, this_week_visits=3,
    ))
    db.commit()


def seed_pt_packages(db: Session) -> None:
    """Gói tập PT tính theo số buổi."""
    if db.query(PTPackage).count() > 0:
        return

    packages = [
        PTPackage(
            name="Gói PT 12 buổi - Khởi động", sessions=12, price=4800000,
            validity_days=90, tier="standard", includes_inbody=True,
            description="Phù hợp người mới bắt đầu, làm quen kỹ thuật cơ bản.",
        ),
        PTPackage(
            name="Gói PT 36 buổi - Tăng cơ", sessions=36, price=12600000,
            validity_days=180, tier="gold", includes_inbody=True,
            includes_nutrition=True,
            description="Lộ trình tăng cơ bài bản với theo dõi InBody định kỳ.",
        ),
        PTPackage(
            name="Gói PT 50 buổi - Siết mỡ", sessions=50, price=16000000,
            validity_days=240, tier="gold", includes_inbody=True,
            includes_nutrition=True,
            description="Chuyên sâu giảm mỡ, kèm tư vấn dinh dưỡng cá nhân hoá.",
        ),
        PTPackage(
            name="Gói PT 100 buổi - VIP Toàn diện", sessions=100, price=28000000,
            validity_days=365, tier="vip", includes_inbody=True,
            includes_nutrition=True,
            description="Đồng hành cả năm, bao gồm dinh dưỡng và phục hồi.",
        ),
    ]
    for pkg in packages:
        pkg.price_per_session = round(pkg.price / pkg.sessions, 0)
        db.add(pkg)
    db.commit()


def seed_trainer_shifts(db: Session) -> None:
    """Ca làm việc của toàn bộ HLV."""
    if db.query(TrainerShift).count() > 0:
        return

    for trainer in db.query(Trainer).all():
        for weekday in (0, 2, 4):  # Thứ 2, Thứ 4, Thứ 6
            db.add(TrainerShift(
                trainer_id=trainer.id, branch_id=trainer.branch_id,
                weekday=weekday, start_hour=6, end_hour=11,
            ))
            db.add(TrainerShift(
                trainer_id=trainer.id, branch_id=trainer.branch_id,
                weekday=weekday, start_hour=17, end_hour=21,
            ))
    db.commit()


def seed_products(db: Session) -> None:
    """Hàng hóa Pro-Shop (kèm 2 sản phẩm tồn kho thấp và sắp hết hạn để demo cảnh báo)."""
    if db.query(Product).count() > 0:
        return

    today = date.today()
    db.add_all([
        Product(
            sku="WHEY-001", name="Whey Protein Isolate 2kg", category="supplement",
            brand="Optimum Nutrition", unit="hũ", servings_per_unit=66,
            price=1850000, serving_price=35000, cost_price=1400000,
            stock_quantity=24, low_stock_threshold=5,
            expiry_date=today + timedelta(days=400),
            description="27g đạm mỗi muỗng, hấp thu nhanh, ít đường.",
        ),
        Product(
            sku="WHEY-002", name="Whey Protein Blend 1kg", category="supplement",
            brand="HealthyGym", unit="hũ", servings_per_unit=33,
            price=890000, serving_price=32000, cost_price=650000,
            stock_quantity=38, low_stock_threshold=8,
            expiry_date=today + timedelta(days=300),
        ),
        Product(
            sku="CREA-001", name="Creatine Monohydrate 300g", category="supplement",
            brand="HealthyGym", unit="hũ", servings_per_unit=60,
            price=550000, serving_price=12000, cost_price=380000,
            stock_quantity=42, low_stock_threshold=10,
            expiry_date=today + timedelta(days=500),
        ),
        # Tồn kho thấp + sắp hết hạn -> demo cảnh báo của hệ thống
        Product(
            sku="PRE-001", name="Pre-Workout 300g", category="supplement",
            brand="HealthyGym", unit="hũ", servings_per_unit=30,
            price=620000, serving_price=25000, cost_price=430000,
            stock_quantity=4, low_stock_threshold=6,
            expiry_date=today + timedelta(days=25),
            description="Tăng tập trung và sức bền cho buổi tập nặng.",
        ),
        Product(
            sku="DRINK-001", name="Nước khoáng Aquafina 500ml", category="drink",
            unit="chai", price=10000, cost_price=6000,
            stock_quantity=180, low_stock_threshold=40,
        ),
        Product(
            sku="DRINK-002", name="Nước tăng lực Revive 500ml", category="drink",
            unit="chai", price=15000, cost_price=9500,
            stock_quantity=140, low_stock_threshold=30,
        ),
        Product(
            sku="ACC-001", name="Găng tay tập Gym", category="accessory",
            unit="đôi", price=250000, cost_price=140000,
            stock_quantity=18, low_stock_threshold=5,
        ),
        Product(
            sku="ACC-002", name="Đai lưng tập tạ", category="accessory",
            unit="cái", price=450000, cost_price=280000,
            stock_quantity=12, low_stock_threshold=4,
        ),
        Product(
            sku="ACC-003", name="Dây kháng lực (bộ 5 mức)", category="accessory",
            unit="bộ", price=320000, cost_price=180000,
            stock_quantity=3, low_stock_threshold=5,
        ),
    ])
    db.commit()


def seed_lockers(db: Session, member) -> None:
    """Tủ đồ dùng theo ngày + tủ cố định cho thuê."""
    if db.query(Locker).count() > 0:
        return

    branch = member.home_branch if member else db.query(Branch).first()
    branch_id = branch.id if branch else None

    lockers = []
    for i in range(1, 31):
        is_male = i <= 15
        lockers.append(Locker(
            code=f"{'M' if is_male else 'F'}{100 + i}",
            branch_id=branch_id,
            zone="male" if is_male else "female",
            kind="daily",
            is_available=True,
        ))
    for i in range(1, 9):
        lockers.append(Locker(
            code=f"VIP{i:02d}", branch_id=branch_id, zone="vip",
            kind="private", is_available=True, monthly_fee=300000,
        ))
    db.add_all(lockers)
    db.commit()


def seed_badges(db: Session) -> None:
    """Huy hiệu thành tích."""
    if db.query(Badge).count() > 0:
        return

    db.add_all([
        Badge(
            code="FIRST_CHECKIN", name="Khởi đầu thuận lợi",
            description="Hoàn thành buổi tập đầu tiên tại phòng gym.",
            category="consistency", criteria_type="checkin_count",
            criteria_value=1, point_reward=20,
        ),
        Badge(
            code="STREAK_4", name="Bền bỉ 4 tuần",
            description="Duy trì chuỗi 4 tuần tập luyện liên tiếp.",
            category="consistency", criteria_type="streak",
            criteria_value=4, point_reward=100,
        ),
        Badge(
            code="STREAK_12", name="Chiến thần kiên trì",
            description="Duy trì chuỗi 12 tuần tập luyện liên tiếp.",
            category="consistency", criteria_type="streak",
            criteria_value=12, point_reward=400,
        ),
        Badge(
            code="CHECKIN_50", name="Nửa trăm buổi tập",
            description="Hoàn thành 50 buổi tập tại phòng gym.",
            category="consistency", criteria_type="checkin_count",
            criteria_value=50, point_reward=250,
        ),
        Badge(
            code="VOLUME_10K", name="Khối lượng khủng",
            description="Tích luỹ 10.000kg khối lượng tập luyện.",
            category="strength", criteria_type="volume",
            criteria_value=10000, point_reward=150,
        ),
        Badge(
            code="VOLUME_100K", name="Cỗ máy tập luyện",
            description="Tích luỹ 100.000kg khối lượng tập luyện.",
            category="strength", criteria_type="volume",
            criteria_value=100000, point_reward=500,
        ),
        Badge(
            code="POINTS_1000", name="Người tích luỹ",
            description="Tích luỹ 1.000 điểm thưởng.",
            category="social", criteria_type="points",
            criteria_value=1000, point_reward=50,
        ),
    ])
    db.commit()


def seed_rewards(db: Session) -> None:
    """Quà đổi bằng điểm thưởng."""
    if db.query(Reward).count() > 0:
        return

    db.add_all([
        Reward(
            name="1 muỗng Whey tại quầy Bar", points_cost=150,
            kind="product", value_amount=35000, stock=0,
            description="Đổi điểm lấy 1 muỗng Whey pha sẵn tại quầy Bar.",
        ),
        Reward(
            name="Voucher giảm 100.000đ khi gia hạn", points_cost=500,
            kind="voucher", value_amount=100000, stock=50,
            description="Áp dụng khi gia hạn gói tập từ 3 tháng trở lên.",
        ),
        Reward(
            name="1 buổi tập PT miễn phí", points_cost=1500,
            kind="pt_session", value_amount=400000, stock=20,
            description="Buổi tập 1-1 60 phút với Huấn luyện viên.",
        ),
        Reward(
            name="Khăn tập HealthyGym cao cấp", points_cost=800,
            kind="product", value_amount=150000, stock=30,
        ),
        Reward(
            name="Thuê tủ cố định 1 tháng", points_cost=1200,
            kind="service", value_amount=300000, stock=10,
            description="Tủ cố định VIP để đồ tập cá nhân trong 1 tháng.",
        ),
    ])
    db.commit()


def seed_challenges(db: Session) -> None:
    """Thử thách biến đổi hình thể 90 ngày."""
    if db.query(Challenge).count() > 0:
        return

    today = date.today()
    db.add(Challenge(
        name="Thử thách Lột xác 90 ngày",
        description=(
            "Thử thách biến đổi hình thể 90 ngày dành cho toàn bộ hội viên. "
            "Cập nhật ảnh Before/After và chỉ số InBody đầu kỳ - cuối kỳ để bình chọn. "
            "Điểm được tính theo mức giảm mỡ, tăng cơ và mức giảm cân an toàn."
        ),
        kind="transformation",
        start_date=today - timedelta(days=15),
        end_date=today + timedelta(days=75),
        max_participants=200,
        entry_fee=0,
        prize_description=(
            "Giải nhất: 6 tháng gói VIP + 20 buổi PT. "
            "Giải nhì: 3 tháng gói Gold + 10 buổi PT. "
            "Giải ba: 1 tháng gói Gold + 5 buổi PT."
        ),
        reward_points=1000,
    ))
    db.commit()


def seed_leads(db: Session) -> None:
    """Khách tập thử trải đều các bước của pipeline CRM."""
    if db.query(Lead).count() > 0:
        return

    rows = [
        ("Nguyễn Văn Hùng", "0912345678", LeadStage.NEW, None),
        ("Trần Thị Mai", "0923456789", LeadStage.SCHEDULED, "Lễ tân Nguyễn Hoàng"),
        ("Lê Minh Tuấn", "0934567890", LeadStage.FIRST_VISIT, "Lễ tân Nguyễn Hoàng"),
        ("Phạm Thu Hà", "0945678901", LeadStage.INBODY_CONSULTED, "Lễ tân Nguyễn Hoàng"),
        ("Võ Hoàng Nam", "0956789012", LeadStage.WON, "Lễ tân Nguyễn Hoàng"),
        ("Đặng Thị Lan", "0967890123", LeadStage.LOST, "Lễ tân Nguyễn Hoàng"),
    ]
    for name, phone, stage, assigned in rows:
        db.add(Lead(
            full_name=name,
            phone=phone,
            source="website",
            stage=stage,
            assigned_to=assigned,
            lost_reason=(
                "Đã có thẻ tập ở phòng gym khác gần nhà hơn"
                if stage == LeadStage.LOST else None
            ),
        ))
    db.commit()


def seed_class_schedules(db: Session) -> None:
    """Buổi học GroupX cụ thể trong 14 ngày tới."""
    if db.query(ClassSchedule).count() > 0:
        return

    today = date.today()
    hours = [(7, 8), (18, 19), (19, 20)]

    for klass in db.query(GymClass).all():
        for offset in range(1, 15):
            the_date = today + timedelta(days=offset)
            if the_date.weekday() == 6:  # Nghỉ Chủ Nhật
                continue

            start_h, end_h = hours[offset % len(hours)]
            start = datetime.combine(the_date, datetime.min.time()).replace(hour=start_h)
            end = start + timedelta(hours=end_h - start_h)

            requires_spot = klass.category in ("Yoga", "Boxing")
            db.add(ClassSchedule(
                gym_class_id=klass.id,
                trainer_id=klass.trainer_id,
                branch_id=klass.branch_id,
                studio=klass.room or "Studio A",
                start_time=start,
                end_time=end,
                capacity=klass.capacity or 25,
                difficulty="beginner" if klass.category == "Yoga" else "intermediate",
                requires_spot_selection=requires_spot,
                spot_layout="mat" if requires_spot else "none",
                status=ScheduleStatus.SCHEDULED,
            ))
    db.commit()


def seed_machine_qrs(db: Session) -> None:
    """Mã QR trên từng máy tập kèm hướng dẫn sử dụng chi tiết."""
    if db.query(MachineQR).count() > 0:
        return

    cardio = db.query(Facility).filter(Facility.category == "Cardio").first()
    strength = db.query(Facility).filter(Facility.category == "Strength").first()

    if cardio:
        db.add(MachineQR(
            facility_id=cardio.id,
            qr_code="MQ-TREADMILL-07",
            machine_code="TREADMILL-07",
            display_name="Máy chạy bộ số 07",
            target_muscles="Chân, Mông, Tim mạch",
            difficulty="beginner",
            exercise_name="Máy chạy bộ",
            video_url="https://www.youtube.com/watch?v=demo-treadmill",
            setup_guide=(
                "1. Bấm nút START để khởi động ở tốc độ 3 km/h.\n"
                "2. Dùng mũi tên để tăng tốc độ và độ dốc.\n"
                "3. Bấm nút INCLINE để điều chỉnh độ dốc.\n"
                "4. Bấm STOP để dừng an toàn."
            ),
            posture_guide=(
                "Giữ thân người thẳng đứng, không bám tay vịn.\n"
                "Bước chân giữa băng tải, mắt nhìn về trước.\n"
                "Vung tay tự nhiên theo nhịp bước."
            ),
            common_mistakes=(
                "❌ Bám chặt tay vịn suốt buổi — làm giảm 20-30% hiệu quả đốt calo.\n"
                "❌ Nhìn xuống chân gây mỏi cổ.\n"
                "❌ Tăng tốc độ đột ngột khi chưa khởi động.\n"
                "❌ Nhảy xuống khi băng tải còn chạy."
            ),
        ))

    if strength:
        db.add(MachineQR(
            facility_id=strength.id,
            qr_code="MQ-SQUAT-RACK-01",
            machine_code="SQUAT-RACK-01",
            display_name="Giàn Squat số 01",
            target_muscles="Đùi trước, Mông, Đùi sau, Core",
            difficulty="intermediate",
            exercise_name="Barbell Back Squat (Squat tạ đòn)",
            setup_guide=(
                "1. Chỉnh giá đỡ ngang tầm vai.\n"
                "2. Chỉnh thanh an toàn cao hơn vị trí đáy khoảng 5cm.\n"
                "3. Chọn tạ phù hợp và khoá chốt hai đầu.\n"
                "4. Bước vào, đặt đòn lên cơ thang sau."
            ),
            posture_guide=(
                "Bàn chân rộng bằng vai, mũi chân hơi xoay ra ngoài 15-30 độ.\n"
                "Siết core, giữ lưng trung lập suốt chuyển động.\n"
                "Hạ tới khi đùi song song sàn, gối đi theo hướng mũi chân."
            ),
            common_mistakes=(
                "❌ Gối đổ vào trong khi đứng lên — nguy cơ chấn thương ACL.\n"
                "❌ Nhấc gót chân khỏi sàn.\n"
                "❌ Cong lưng dưới ở vị trí đáy.\n"
                "❌ Nhìn xuống hoặc ngửa cổ lên trong khi squat."
            ),
        ))
    db.commit()


def seed_parq(db: Session, member) -> None:
    """Phiếu sàng lọc PAR-Q mẫu (không chống chỉ định) cho hội viên demo."""
    if not member:
        return
    if db.query(PARQScreening).filter(PARQScreening.member_id == member.id).count() > 0:
        return

    db.add(PARQScreening(
        member_id=member.id,
        screened_at=date.today() - timedelta(days=12),
        risk_level="low",
        needs_medical_clearance=False,
        contraindications_json=json.dumps([]),
        safe_exercise_notes_json=json.dumps(
            ["Không có chống chỉ định y tế. Đủ điều kiện tập luyện bình thường."],
            ensure_ascii=False,
        ),
        screened_by="self",
    ))
    db.commit()


def seed_erp_data(db: Session, member) -> None:
    """Điều phối toàn bộ dữ liệu mẫu ERP."""
    ensure_role_accounts(db)
    seed_contracts(db, member)
    seed_pt_packages(db)
    seed_trainer_shifts(db)
    seed_products(db)
    seed_lockers(db, member)
    seed_badges(db)
    seed_rewards(db)
    seed_challenges(db)
    seed_leads(db)
    seed_class_schedules(db)
    seed_machine_qrs(db)
    seed_parq(db, member)