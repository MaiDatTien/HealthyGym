from datetime import date
from django.db import models
from django.contrib.auth.models import User

# 1. Hệ thống Chi nhánh
class Branch(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên chi nhánh")
    address = models.CharField(max_length=255, verbose_name="Địa chỉ")
    phone = models.CharField(max_length=15, verbose_name="Hotline")
    opening_hours = models.CharField(max_length=100, default="05:30 - 22:00", verbose_name="Giờ mở cửa")
    image_url = models.URLField(max_length=500, verbose_name="Ảnh chi nhánh")

    def __str__(self):
        return self.name

# 2. Hệ thống Hội viên
class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    membership_type = models.CharField(
        max_length=10, 
        choices=[('STD', 'Standard'), ('VIP', 'VIP')],
        default='STD'
    )
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Chi nhánh đăng ký")
    join_date = models.DateField(auto_now_add=True)
    expire_date = models.DateField(null=True, blank=True, verbose_name="Ngày hết hạn")

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def is_active(self):
        if self.expire_date:
            return self.expire_date >= date.today()
        return False

# 3. Chỉ số sức khỏe & BMI
class HealthRecord(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    date_recorded = models.DateField(auto_now_add=True)
    weight = models.FloatField(help_text="Cân nặng (kg)")
    height = models.FloatField(help_text="Chiều cao (cm)")
    body_fat = models.FloatField(help_text="Tỷ lệ mỡ (%)", null=True, blank=True)

    def __str__(self):
        return f"{self.member} - {self.date_recorded}"

    @property
    def bmi(self):
        if self.height and self.height > 0:
            height_m = self.height / 100
            return round(self.weight / (height_m ** 2), 1)
        return 0

    @property
    def bmi_status(self):
        val = self.bmi
        if val < 18.5:
            return ('Thiếu cân', 'warning')
        elif 18.5 <= val < 24.9:
            return ('Bình thường', 'success')
        elif 25 <= val < 29.9:
            return ('Thừa cân', 'danger')
        else:
            return ('Béo phì', 'dark')

# 4. Gói tập nâng cao & Đơn hàng
class MembershipPlan(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên gói tập")
    price = models.IntegerField(verbose_name="Giá tiền (VNĐ)")
    duration_days = models.IntegerField(default=30, verbose_name="Thời hạn (Số ngày)")
    description = models.TextField(verbose_name="Mô tả quyền lợi")
    is_popular = models.BooleanField(default=False, verbose_name="Gói nổi bật")

    def __str__(self):
        return f"{self.name} - {self.price:,}đ"

class SubscriptionOrder(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    plan = models.ForeignKey(MembershipPlan, on_delete=models.CASCADE)
    amount = models.IntegerField(verbose_name="Số tiền thanh toán")
    payment_method = models.CharField(
        max_length=20,
        choices=[('TRANSFER', 'Chuyển khoản QR'), ('CASH', 'Tiền mặt tại quầy')],
        default='TRANSFER'
    )
    status = models.CharField(
        max_length=20,
        choices=[('PENDING', 'Chờ thanh toán'), ('PAID', 'Đã thanh toán'), ('CANCELLED', 'Đã hủy')],
        default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Đơn #{self.id} - {self.member.user.username}"

# 5. Huấn luyện viên
class Trainer(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên HLV")
    specialty = models.CharField(max_length=100, verbose_name="Chuyên môn")
    experience = models.IntegerField(verbose_name="Năm kinh nghiệm")
    bio = models.TextField(verbose_name="Giới thiệu bản thân")
    image_url = models.URLField(max_length=500, verbose_name="Đường dẫn ảnh")

    def __str__(self):
        return self.name

# 6. Lớp học GroupX & Lịch học
class GymClass(models.Model):
    DAY_CHOICES = [
        ('MON', 'Thứ Hai'),
        ('TUE', 'Thứ Ba'),
        ('WED', 'Thứ Tư'),
        ('THU', 'Thứ Năm'),
        ('FRI', 'Thứ Sáu'),
        ('SAT', 'Thứ Bảy'),
        ('SUN', 'Chủ Nhật'),
    ]
    title = models.CharField(max_length=100, verbose_name="Tên lớp học")
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, verbose_name="HLV Phụ trách")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name="Chi nhánh")
    day_of_week = models.CharField(max_length=3, choices=DAY_CHOICES, verbose_name="Ngày học")
    start_time = models.TimeField(verbose_name="Giờ bắt đầu")
    end_time = models.TimeField(verbose_name="Giờ kết thúc")
    max_capacity = models.IntegerField(default=20, verbose_name="Số lượng học viên tối đa")

    def __str__(self):
        return f"{self.title} - {self.get_day_of_week_display()} ({self.start_time.strftime('%H:%M')})"

    @property
    def enrolled_count(self):
        return self.classenrollment_set.count()

    @property
    def is_full(self):
        return self.enrolled_count >= self.max_capacity

class ClassEnrollment(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    gym_class = models.ForeignKey(GymClass, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('member', 'gym_class')

    def __str__(self):
        return f"{self.member} -> {self.gym_class.title}"

# 7. Nhật ký điểm danh (Check-in Logs)
class CheckInLog(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    checkin_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member} - {self.checkin_time.strftime('%d/%m/%Y %H:%M')}"

# 8. Cơ sở vật chất, Tin tức, Đặt lịch & Đánh giá
class Facility(models.Model):
    CATEGORY_CHOICES = [
        ('CARDIO', 'Khu Cardio'),
        ('WEIGHTS', 'Khu Tập Tạ'),
        ('STUDIO', 'Phòng Yoga & GroupX'),
        ('RELAX', 'Tiện Ích & Xông Hơi'),
    ]
    name = models.CharField(max_length=100, verbose_name="Tên thiết bị")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='CARDIO')
    description = models.TextField(verbose_name="Mô tả")
    image_url = models.URLField(max_length=500, verbose_name="Đường dẫn ảnh")

    def __str__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=200, verbose_name="Tiêu đề")
    summary = models.CharField(max_length=300, verbose_name="Tóm tắt")
    content = models.TextField(verbose_name="Nội dung")
    image_url = models.URLField(max_length=500, verbose_name="Ảnh bìa")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Booking(models.Model):
    SERVICE_CHOICES = [
        ('TRIAL', 'Tập thử miễn phí'),
        ('PT', 'Thuê HLV Cá Nhân (1:1)'),
        ('YOGA', 'Lớp GroupX / Yoga'),
    ]
    full_name = models.CharField(max_length=100, verbose_name="Họ tên")
    phone = models.CharField(max_length=15, verbose_name="Số điện thoại")
    email = models.EmailField(blank=True, null=True)
    service = models.CharField(max_length=20, choices=SERVICE_CHOICES, default='TRIAL')
    booking_date = models.DateField(verbose_name="Ngày hẹn")
    note = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, 
        choices=[('PENDING', 'Chờ liên hệ'), ('CONFIRMED', 'Đã xác nhận'), ('CANCELLED', 'Đã hủy')],
        default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.get_service_display()}"

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    rating = models.IntegerField(choices=[(i, f"{i} Sao ⭐") for i in range(1, 6)], default=5)
    comment = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.rating} Sao)"

class FAQ(models.Model):
    question = models.CharField(max_length=255, verbose_name="Câu hỏi")
    answer = models.TextField(verbose_name="Câu trả lời")
    order = models.IntegerField(default=0, verbose_name="Thứ tự hiển thị")

    def __str__(self):
        return self.question