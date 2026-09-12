from django import forms
from django.contrib.auth.models import User
from .models import MembershipPlan, Member, HealthRecord, Booking, Feedback, Trainer, Branch, GymClass

class TrainerForm(forms.ModelForm):
    class Meta:
        model = Trainer
        fields = ['name', 'specialty', 'experience', 'bio', 'image_url']
        labels = {
            'name': 'Tên HLV',
            'specialty': 'Chuyên môn (VD: Gym, Yoga)',
            'experience': 'Số năm kinh nghiệm',
            'bio': 'Giới thiệu',
            'image_url': 'Link ảnh HLV',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tên HLV'}),
            'specialty': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: Gym / Fitness'}),
            'experience': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Số năm'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mô tả HLV...'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
        }

class MembershipPlanForm(forms.ModelForm):
    class Meta:
        model = MembershipPlan
        fields = ['name', 'price', 'duration_days', 'description', 'is_popular']
        labels = {
            'name': 'Tên gói / Sản phẩm',
            'price': 'Giá bán (VNĐ)',
            'duration_days': 'Thời hạn (Số ngày)',
            'description': 'Mô tả chi tiết',
            'is_popular': 'Đánh dấu là gói Nổi Bật',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: Gói VIP 3 Tháng'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: 1500000'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: 90'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Nhập quyền lợi gói...'}),
            'is_popular': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Mật khẩu")
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'class': 'form-control'}), label="Số điện thoại")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            Member.objects.create(
                user=user,
                phone=self.cleaned_data["phone"],
                membership_type='STD' 
            )
        return user

class HealthRecordForm(forms.ModelForm):
    class Meta:
        model = HealthRecord
        fields = ['weight', 'height', 'body_fat']
        widgets = {
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '20'}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '100'}),
            'body_fat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['full_name', 'phone', 'email', 'service', 'booking_date', 'note']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'service': forms.Select(attrs={'class': 'form-select'}),
            'booking_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['name', 'rating', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# --- FORM MỚI BỔ SUNG ---
class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name', 'address', 'phone', 'opening_hours', 'image_url']
        labels = {
            'name': 'Tên chi nhánh', 'address': 'Địa chỉ', 'phone': 'Hotline', 
            'opening_hours': 'Giờ mở cửa', 'image_url': 'Link ảnh'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'opening_hours': forms.TextInput(attrs={'class': 'form-control'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control'}),
        }

class GymClassForm(forms.ModelForm):
    class Meta:
        model = GymClass
        fields = ['title', 'trainer', 'branch', 'day_of_week', 'start_time', 'end_time', 'max_capacity']
        labels = {
            'title': 'Tên lớp', 'trainer': 'Huấn luyện viên', 'branch': 'Chi nhánh', 
            'day_of_week': 'Thứ', 'start_time': 'Giờ bắt đầu', 'end_time': 'Giờ kết thúc', 'max_capacity': 'Số lượng tối đa'
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'trainer': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'max_capacity': forms.NumberInput(attrs={'class': 'form-control'}),
        }