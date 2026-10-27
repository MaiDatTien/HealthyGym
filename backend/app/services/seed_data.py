from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from app.models.user import User, Member, Trainer
from app.models.listing import Branch, Facility, MembershipPlan, GymClass, Article
from app.models.interaction import Voucher, Feedback, Order, Booking
from app.models.ai import AIPlan, DailyCheckin, HealthMetric, WorkoutLog
from app.models.pt import CoachNote, EquipmentMaintenance, PTBooking, TrainerSlot
from app.security import get_password_hash
from app.services.seed_erp import ensure_role_accounts, seed_erp_data


def seed_ai_metrics(db: Session, member: Member) -> None:
    """Sinh chuỗi chỉ số cơ thể lịch sử 12 tuần để biểu đồ tiến độ có dữ liệu.

    Mô phỏng một hội viên giảm mỡ thành công: cân nặng giảm, Body Fat giảm,
    khối lượng cơ nạp tăng nhẹ (đúng kịch bản Body Recomposition).
    """
    if db.query(HealthMetric).filter(HealthMetric.member_id == member.id).count() > 0:
        return

    import random

    random.seed(42)  # dữ liệu mẫu ổn định giữa các lần seed

    today = date.today()
    start_weight, start_bf = 78.5, 26.4
    height = 172.0

    for week in range(12, -1, -1):
        measured = today - timedelta(days=week * 7)
        progress = (12 - week) / 12.0
        weight = round(start_weight - 5.2 * progress + random.uniform(-0.25, 0.25), 1)
        body_fat = round(start_bf - 6.1 * progress + random.uniform(-0.2, 0.2), 1)
        lbm = round(weight * (1 - body_fat / 100), 2)
        fat_mass = round(weight - lbm, 2)
        bmi = round(weight / ((height / 100) ** 2), 2)
        lbm_kg = lbm
        bmr = round(370 + 21.6 * lbm_kg, 1)

        category = "Skinny Fat - Thừa mỡ nhưng thiếu cơ"
        if body_fat < 20:
            category = "Average - Trung bình, cần cải thiện tỷ lệ cơ/mỡ"
        if body_fat < 17:
            category = "Lean - Gọn gàng, ít mỡ"

        db.add(
            HealthMetric(
                member_id=member.id,
                measured_at=measured,
                height_cm=height,
                weight_kg=weight,
                body_fat_percentage=body_fat,
                age=29,
                gender="male",
                muscle_mass_kg=lbm,
                visceral_fat_level=max(4.0, round(11.5 - 5.5 * progress, 1)),
                waist_cm=round(88.0 - 7.5 * progress, 1),
                neck_cm=38.5,
                body_water_kg=round(weight * 0.55, 1),
                bmi=bmi,
                lean_body_mass_kg=lbm,
                fat_mass_kg=fat_mass,
                bmr_kcal=bmr,
                tdee_kcal=round(bmr * 1.55, 1),
                body_type_classification=category,
                source="inbody" if week % 4 == 0 else "manual",
                note="Đo InBody định kỳ tại phòng tập" if week % 4 == 0 else "Tự cân tại nhà",
            )
        )

        # Nhật ký dinh dưỡng & giấc ngủ trong 30 ngày gần nhất
        if week <= 4:
            db.add(
                DailyCheckin(
                    member_id=member.id,
                    log_date=measured,
                    calories_in=round(1950 + random.uniform(-220, 220)),
                    protein_g=round(152 + random.uniform(-18, 18)),
                    carbs_g=round(192 + random.uniform(-25, 25)),
                    fat_g=round(62 + random.uniform(-10, 10)),
                    water_liters=round(3.1 + random.uniform(-0.4, 0.5), 1),
                    sleep_hours=round(7.4 + random.uniform(-0.8, 1.0), 1),
                    steps=round(8600 + random.uniform(-2200, 2600)),
                    weight_kg=weight,
                    mood="Tốt",
                )
            )

    # Nhật ký tập luyện với Progressive Overload (tạ tăng dần theo tuần)
    if db.query(WorkoutLog).filter(WorkoutLog.member_id == member.id).count() == 0:
        progression = [
            ("Incline Dumbbell Press (Đẩy tạ đơn ghế dốc lên)", "Ngực trên, Vai trước, Tay sau", 22.5, 30.0, 8),
            ("Lat Pulldown (Kéo cáp xô rộng tay)", "Cơ xô (Lats), Tay trước", 45.0, 57.5, 10),
            ("Barbell Back Squat (Squat tạ đòn)", "Đùi trước, Mông, Đùi sau", 60.0, 80.0, 8),
            ("Seated Dumbbell Shoulder Press (Đẩy vai tạ đơn ngồi)", "Vai trước, Vai giữa", 16.0, 20.0, 10),
            ("Romanian Deadlift (Deadlift Rumani tạ đòn)", "Đùi sau, Mông", 55.0, 72.5, 8),
            ("Barbell Biceps Curl (Cuốn tay trước tạ đòn)", "Tay trước (Biceps)", 20.0, 27.5, 10),
        ]
        for week_offset in range(6, -1, -1):
            log_date = today - timedelta(days=week_offset * 7)
            progress = (6 - week_offset) / 6.0
            for name, muscle, start_w, end_w, reps in progression:
                weight = round((start_w + (end_w - start_w) * progress) * 2) / 2
                db.add(
                    WorkoutLog(
                        member_id=member.id,
                        log_date=log_date,
                        session_focus="Upper / Lower Split",
                        exercise_name=name,
                        target_muscle=muscle,
                        sets=4,
                        reps=reps,
                        weight_kg=weight,
                        rpe=round(7.5 + progress * 1.0, 1),
                        duration_minutes=62,
                        calories_burned=round(420 + progress * 40),
                        notes="Kỹ thuật tốt, cảm nhận cơ rõ" if progress > 0.5 else "Làm quen động tác",
                    )
                )

    db.commit()


def seed_trainer_slots(db: Session, trainers: list) -> None:
    """Mở khung giờ dạy 1-1 cho các HLV trong 14 ngày tới."""
    if db.query(TrainerSlot).count() > 0:
        return

    today = date.today()
    hours = [(6, 7), (7, 8), (9, 10), (17, 18), (18, 19), (19, 20)]
    for trainer in trainers:
        for day_offset in range(0, 14):
            slot_date = today + timedelta(days=day_offset)
            # Nghỉ Chủ Nhật
            if slot_date.weekday() == 6:
                continue
            for start_h, end_h in hours:
                start = datetime.combine(slot_date, datetime.min.time()).replace(hour=start_h)
                end = datetime.combine(slot_date, datetime.min.time()).replace(hour=end_h)
                db.add(
                    TrainerSlot(
                        trainer_id=trainer.id,
                        branch_id=trainer.branch_id,
                        start_time=start,
                        end_time=end,
                        is_booked=False,
                        note="Buổi tập 1-1 — 60 phút",
                    )
                )
    db.commit()

def seed_initial_data(db: Session):
    # 1. ĐẢM BẢO TÀI KHOẢN ADMIN GỐC LUÔN LÀ tk: admin / mk: 123
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            email="admin@healthygym.vn",
            full_name="Quản trị viên Hệ thống (Admin)",
            hashed_password=get_password_hash("123"),
            role="admin",
            is_active=True
        )
        db.add(admin_user)
    else:
        admin_user.hashed_password = get_password_hash("123")
        admin_user.role = "admin"
        admin_user.is_active = True
    db.commit()

    # Nếu đã có gói tập => hệ thống đã được khởi tạo trước đó.
    # Vẫn phải đảm bảo dữ liệu cho phân hệ AI & PT 1-1 tồn tại.
    if db.query(MembershipPlan).count() > 0:
        seed_ai_extras(db)
        return

    staff_user = User(username="staff", email="staff@healthygym.vn", full_name="Lễ tân Nguyễn Hoàng", hashed_password=get_password_hash("123"), role="receptionist")
    receptionist_user = User(username="letan", email="letan@healthygym.vn", full_name="Lễ tân & Tư vấn Nguyễn Hoàng", hashed_password=get_password_hash("123"), role="receptionist")
    facility_user = User(username="csvc", email="csvc@healthygym.vn", full_name="Quản lý CSVC Trần Văn Khoa", hashed_password=get_password_hash("123"), role="facility_manager")
    member_user = User(username="hoivien", email="dat@healthygym.vn", full_name="Mai Tiến Đạt", hashed_password=get_password_hash("123"), role="member")
    trainer_user = User(username="hlv", email="hlv@healthygym.vn", full_name="HLV Trần Quốc Tuấn", hashed_password=get_password_hash("123"), role="trainer")
    db.add_all([staff_user, receptionist_user, facility_user, member_user, trainer_user])
    db.commit()

    b1 = Branch(name="HealthyGym Quận 1 - Nguyễn Huệ (TP. Hồ Chí Minh)", address="123 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh", phone="1900 636920", opening_hours="Mở cửa 24/7")
    b2 = Branch(name="HealthyGym Tân Bình - Hoàng Văn Thụ (TP. Hồ Chí Minh)", address="431A Hoàng Văn Thụ, Quận Tân Bình, TP. Hồ Chí Minh", phone="1900 636920", opening_hours="Mở cửa 24/7")
    b3 = Branch(name="HealthyGym Đà Nẵng - Hải Châu", address="256 Điện Biên Phủ, Quận Hải Châu, Đà Nẵng", phone="1900 636920", opening_hours="Mở cửa 24/7")
    b4 = Branch(name="HealthyGym Cần Thơ - Ninh Kiều", address="88 Mậu Thân, Quận Ninh Kiều, Cần Thơ", phone="1900 636920", opening_hours="Mở cửa 24/7")
    b5 = Branch(name="HealthyGym Đồng Nai - Biên Hòa", address="102 Phạm Văn Thuận, TP. Biên Hòa, Đồng Nai", phone="1900 636920", opening_hours="Mở cửa 24/7")
    db.add_all([b1, b2, b3, b4, b5])
    db.commit()

    p1 = MembershipPlan(
        name="GÓI 1 THÁNG - LINH HOẠT",
        duration_days=30,
        price=399000,
        benefits="1 chi nhánh tự chọn, Tập luyện 24/7 không giới hạn, Miễn phí các lớp tập nhóm, Miễn phí Wifi / Nước uống / Gửi xe, Thanh toán tiền mặt hoặc chuyển khoản",
        includes_pt=False,
        is_popular=False
    )
    p2 = MembershipPlan(
        name="GÓI 6 THÁNG - TOÀN HỆ THỐNG",
        duration_days=180,
        price=1799000,
        benefits="Tập mọi chi nhánh trên toàn quốc (Chỉ 299.000đ/tháng - Tiết kiệm 25%), Tập luyện 24/7, Dẫn bạn tập cùng 4 lần/tháng, Giáo án tập luyện trên App, Đo InBody định kỳ & 2 buổi PT hướng dẫn",
        includes_pt=True,
        is_popular=True
    )
    p3 = MembershipPlan(
        name="GÓI 1 THÁNG - TỰ ĐỘNG",
        duration_days=30,
        price=349000,
        benefits="1 chi nhánh tự chọn, Tự động gia hạn qua thẻ JCB/VISA/Mastercard, Tập luyện 24/7, Miễn phí lớp nhóm Yoga/Zumba/HIIT, Miễn phí Nước uống / Gửi xe",
        includes_pt=False,
        is_popular=False
    )
    p4 = MembershipPlan(
        name="GÓI 12 THÁNG - SUPER VIP",
        duration_days=365,
        price=3290000,
        benefits="Tập toàn hệ thống 15+ chi nhánh 24/7, Tặng 6 buổi PT 1-1 chuyên sâu, Bảo lưu thẻ tối đa 60 ngày, Dẫn bạn tập cùng 8 lần/tháng",
        includes_pt=True,
        is_popular=False
    )
    db.add_all([p1, p2, p3, p4])
    db.commit()

    m1 = Member(user_id=member_user.id, full_name="Mai Tiến Đạt", phone="0988112233", email="dat@healthygym.vn", current_plan_id=p2.id, status="active", join_date=date.today() - timedelta(days=10), expire_date=date.today() + timedelta(days=170))
    m2 = Member(full_name="Nguyễn Minh Anh", phone="0912334455", email="minhanh@gmail.com", current_plan_id=p1.id, status="active", join_date=date.today() - timedelta(days=5), expire_date=date.today() + timedelta(days=25))
    db.add_all([m1, m2])
    db.commit()

    t1 = Trainer(full_name="HLV Trần Quốc Tuấn", specialty="Hướng dẫn thiết bị & Tăng cơ", phone="0909111222", experience_years=6, bio="Chuyên gia hình thể NASM Quốc tế, hỗ trợ hội viên mới làm quen máy tập an toàn.", branch_id=b1.id, user_id=trainer_user.id, rating=4.9, certifications="NASM-CPT, ACE Nutrition, Chứng chỉ Kỹ thuật Squat/Deadlift nâng cao")
    t2 = Trainer(full_name="HLV Lê Thảo Vy", specialty="Yoga & Group X", phone="0909333444", experience_years=5, bio="Chứng chỉ Yoga Alliance 500h, phụ trách các lớp tập nhóm năng lượng cao.", branch_id=b2.id, rating=4.8, certifications="Yoga Alliance RYT-500, Pilates Mat, Group Fitness Instructor")
    t3 = Trainer(full_name="HLV Hoàng Gia Bảo", specialty="HIIT, Cardio & Đốt Mỡ", phone="0909555666", experience_years=4, bio="Thiết kế giáo án giảm mỡ siêu tốc và săn chắc vóc dáng.", branch_id=b1.id, rating=4.7, certifications="ISSA-CPT, HIIT Specialist, Boxing Fitness Level 2")
    t4 = Trainer(full_name="HLV Phạm Ngọc Hân", specialty="Dinh dưỡng thể thao & Body Recomposition", phone="0909777888", experience_years=7, bio="Chuyên gia dinh dưỡng thể thao, đồng hành cùng hội viên xây dựng lại tỷ lệ cơ/mỡ.", branch_id=b1.id, rating=5.0, certifications="ISSN Sports Nutrition, Precision Nutrition L2, FMS Level 2")
    db.add_all([t1, t2, t3, t4])
    db.commit()

    c1 = GymClass(name="Hatha Yoga Cho Mọi Người", category="Yoga", schedule_time="Thứ 2, 4, 6 (07:00 - 08:00)", room="Studio Group X", capacity=25, trainer_id=t2.id, branch_id=b1.id, description="Lớp học miễn phí cho hội viên, giúp dẻo dai xương khớp.")
    c2 = GymClass(name="HIIT Đốt Mỡ Toàn Thân", category="HIIT", schedule_time="Thứ 3, 5, 7 (18:30 - 19:30)", room="Khu Functional 24/7", capacity=30, trainer_id=t3.id, branch_id=b1.id, description="Đốt 600-800 kcal mỗi buổi tập cùng âm nhạc sôi động.")
    c3 = GymClass(name="Zumba & Dance Fitness", category="Boxing", schedule_time="Thứ 2, 4, 6 (19:00 - 20:00)", room="Studio Lầu 2", capacity=25, trainer_id=t2.id, branch_id=b2.id, description="Xả stress cực mạnh sau giờ làm việc.")
    c4 = GymClass(name="Hướng Dẫn Kỹ Thuật Tập Tạ Cơ Bản", category="Strength", schedule_time="Thứ 3, 5, 7 (17:30 - 18:30)", room="Khu Free Weight", capacity=20, trainer_id=t1.id, branch_id=b2.id, description="Hướng dẫn sử dụng thiết bị và kỹ thuật Squat, Deadlift chuẩn.")
    db.add_all([c1, c2, c3, c4])
    db.commit()

    f1 = Facility(name="Khu Cardio Máy Chạy Bộ & Xe Đạp 24/7", category="Cardio", quantity=35, status="Hoạt động tốt", description="Trang thiết bị hiện đại, không gian máy lạnh sạch sẽ 24/7.", branch_id=b1.id)
    f2 = Facility(name="Khu Tạ Rời & Giàn Đa Năng Chuẩn Quốc Tế", category="Strength", quantity=20, status="Hoạt động tốt", description="Đầy đủ máy tập cho mọi nhóm cơ từ cơ bản đến nâng cao.", branch_id=b1.id)
    f3 = Facility(name="Tiện Ích Miễn Phí: Nước Uống, Tủ Đồ, Phòng Tắm & Wifi", category="Tiện ích", quantity=100, status="Hoạt động tốt", description="Miễn phí 100% cho toàn bộ hội viên khi đến tập.", branch_id=b1.id)
    db.add_all([f1, f2, f3])
    db.commit()

    v1 = Voucher(code="GIAM10", discount_percent=10, max_discount_amount=300000, is_active=True, valid_until=datetime.utcnow() + timedelta(days=90))
    v2 = Voucher(code="HEALTHY20", discount_percent=20, max_discount_amount=500000, is_active=True, valid_until=datetime.utcnow() + timedelta(days=90))
    fb1 = Feedback(member_name="Mai Tiến Đạt", rating=5, comment="Phòng tập mở cửa 24/7 cực kỳ tiện, giá hợp lý, máy móc mới và không gian rất thân thiện!")
    db.add_all([v1, v2, fb1])
    db.commit()

    # ---- Dữ liệu cho phân hệ AI & PT 1-1 ----
    seed_ai_extras(db)


def seed_ai_extras(db: Session) -> None:
    """Bổ sung dữ liệu cho các phân hệ AI Coach, Progress Tracker và PT 1-1.

    Hàm này idempotent — chạy lại nhiều lần vẫn an toàn.
    """
    # 0a. Đảm bảo tài khoản 6 vai trò tồn tại
    ensure_role_accounts(db)

    # 0b. Đảm bảo tài khoản Huấn luyện viên tồn tại và được liên kết hồ sơ HLV
    trainer_user = db.query(User).filter(User.username == "hlv").first()
    if not trainer_user:
        trainer_user = User(
            username="hlv",
            email="hlv@healthygym.vn",
            full_name="HLV Trần Quốc Tuấn",
            hashed_password=get_password_hash("123"),
            role="trainer",
            is_active=True,
        )
        db.add(trainer_user)
        db.commit()
        db.refresh(trainer_user)
    else:
        trainer_user.role = "trainer"
        trainer_user.hashed_password = get_password_hash("123")
        trainer_user.is_active = True
        db.commit()

    first_trainer = db.query(Trainer).order_by(Trainer.id.asc()).first()
    if first_trainer and not first_trainer.user_id:
        first_trainer.user_id = trainer_user.id
        if not first_trainer.rating:
            first_trainer.rating = 4.9
        db.commit()

    # 1. Gắn HLV phụ trách cho hội viên mẫu
    member = db.query(Member).filter(Member.full_name == "Mai Tiến Đạt").first()
    trainer = first_trainer

    if member and trainer and not member.trainer_id:
        member.trainer_id = trainer.id
        db.commit()

    # 1b. Bổ sung dữ liệu ERP (hợp đồng, sản phẩm, tủ, huy hiệu, gói PT...)
    if member:
        seed_erp_data(db, member)

    # 2. Chuỗi chỉ số cơ thể + nhật ký tập luyện/dinh dưỡng cho biểu đồ tiến độ
    if member:
        seed_ai_metrics(db, member)

    # 3. Khung giờ dạy 1-1 của toàn bộ HLV
    all_trainers = db.query(Trainer).all()
    if all_trainers:
        seed_trainer_slots(db, all_trainers)

    # 4. Phiếu bảo trì thiết bị mẫu
    if db.query(EquipmentMaintenance).count() == 0:
        facility = (
            db.query(Facility)
            .filter(Facility.name.like("%Cardio%"))
            .first()
        )
        if facility:
            db.add_all([
                EquipmentMaintenance(
                    facility_id=facility.id,
                    issue="Máy chạy bộ số 7 có tiếng kêu bất thường ở băng tải khi chạy tốc độ trên 10 km/h.",
                    severity="medium",
                    status="in_progress",
                    reported_by="Lễ tân Nguyễn Hoàng",
                    technician="Kỹ thuật viên Trung",
                    cost=850000,
                ),
                EquipmentMaintenance(
                    facility_id=facility.id,
                    issue="Màn hình cảm ứng máy elliptical số 3 bị liệt điểm chạm góc phải.",
                    severity="low",
                    status="pending",
                    reported_by="HLV Hoàng Gia Bảo",
                ),
            ])
            db.commit()

    # 5. Đánh giá mẫu của HLV cho học viên
    if member and trainer and db.query(CoachNote).count() == 0:
        db.add_all([
            CoachNote(
                trainer_id=trainer.id,
                member_id=member.id,
                note_date=date.today() - timedelta(days=3),
                performance="excellent",
                content="Buổi tập Upper Body A hoàn thành tốt. Tăng được 2.5kg ở Incline Dumbbell Press "
                        "so với tuần trước. Kiểm soát nhịp thở và tempo hạ tạ rất ổn định.",
                next_focus="Tuần sau tăng tải ở Lat Pulldown lên 60kg, chú ý giữ vai ổn định khi kéo.",
            ),
            CoachNote(
                trainer_id=trainer.id,
                member_id=member.id,
                note_date=date.today() - timedelta(days=10),
                performance="good",
                content="Buổi tập Lower Body. Kỹ thuật Squat đã cải thiện rõ, không còn hiện tượng "
                        "gối đổ vào trong. Cần chú ý giữ gót chân bám sàn ở các hiệp nặng.",
                next_focus="Bổ sung bài tập cơ mông-đùi sau để cân bằng lực đẩy của đùi trước.",
            ),
        ])
        db.commit()
