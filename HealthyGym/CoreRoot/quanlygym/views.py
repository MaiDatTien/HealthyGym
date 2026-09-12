from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum
from .models import (
    Member, HealthRecord, Facility, Article, Booking, Feedback, Trainer,
    Branch, MembershipPlan, SubscriptionOrder, GymClass, ClassEnrollment,
    CheckInLog, FAQ
)
from .forms import RegisterForm, HealthRecordForm, BookingForm, FeedbackForm, MembershipPlanForm, TrainerForm, BranchForm, GymClassForm

def dashboard(request):
    total_members = Member.objects.count()
    branches = Branch.objects.all()[:3]
    latest_articles = Article.objects.all().order_by('-created_at')[:3]
    featured_facilities = Facility.objects.all()[:3]
    feedbacks = Feedback.objects.filter(is_approved=True).order_by('-created_at')[:3]
    plans = MembershipPlan.objects.all()[:3]
    
    context = {
        'total_members': total_members,
        'branches': branches,
        'latest_articles': latest_articles,
        'featured_facilities': featured_facilities,
        'feedbacks': feedbacks,
        'plans': plans,
    }
    return render(request, 'quanlygym/dashboard.html', context)

def intro(request):
    return render(request, 'quanlygym/intro.html')

def packages(request):
    plans = MembershipPlan.objects.all()
    return render(request, 'quanlygym/packages.html', {'plans': plans})

def branches_view(request):
    branches = Branch.objects.all()
    return render(request, 'quanlygym/branches.html', {'branches': branches})

def facilities_view(request):
    facilities = Facility.objects.all()
    return render(request, 'quanlygym/facilities.html', {'facilities': facilities})

def news_list_view(request):
    articles = Article.objects.all().order_by('-created_at')
    return render(request, 'quanlygym/news_list.html', {'articles': articles})

def news_detail_view(request, pk):
    article = get_object_or_404(Article, pk=pk)
    return render(request, 'quanlygym/news_detail.html', {'article': article})

def trainers_view(request):
    trainers = Trainer.objects.all()
    return render(request, 'quanlygym/trainers.html', {'trainers': trainers})

def faq_view(request):
    faqs = FAQ.objects.all().order_by('order')
    return render(request, 'quanlygym/faq.html', {'faqs': faqs})

def schedule_view(request):
    classes = GymClass.objects.all().order_by('day_of_week', 'start_time')
    user_enrolled_ids = []
    if request.user.is_authenticated:
        member = Member.objects.filter(user=request.user).first()
        if member:
            user_enrolled_ids = ClassEnrollment.objects.filter(member=member).values_list('gym_class_id', flat=True)
            
    context = {
        'classes': classes,
        'user_enrolled_ids': user_enrolled_ids,
    }
    return render(request, 'quanlygym/schedule.html', context)

# ---------------------------------------------------------
# NGHIỆP VỤ 1: KIỂM SOÁT ĐĂNG KÝ LỚP HỌC CHẶT CHẼ
# ---------------------------------------------------------
@login_required(login_url='/dang-nhap/')
def enroll_class(request, class_id):
    member = get_object_or_404(Member, user=request.user)
    
    # CHẶN: Nếu thẻ hết hạn hoặc chưa mua gói, KHÔNG cho đăng ký
    if not member.is_active:
        messages.error(request, "⛔ LỖI: Bạn phải có gói tập còn hạn để giữ chỗ lớp GroupX!")
        return redirect('packages')

    gym_class = get_object_or_404(GymClass, id=class_id)
    
    if gym_class.is_full:
        messages.error(request, "Lớp học này đã đủ số lượng học viên!")
    else:
        enrollment, created = ClassEnrollment.objects.get_or_create(member=member, gym_class=gym_class)
        if created:
            messages.success(request, f"Đã đăng ký thành công lớp {gym_class.title}!")
        else:
            messages.info(request, "Bạn đã đăng ký lớp học này trước đó.")
    return redirect('schedule')

@login_required(login_url='/dang-nhap/')
def cancel_enrollment(request, class_id):
    member = get_object_or_404(Member, user=request.user)
    gym_class = get_object_or_404(GymClass, id=class_id)
    ClassEnrollment.objects.filter(member=member, gym_class=gym_class).delete()
    messages.warning(request, f"Đã hủy đăng ký lớp {gym_class.title}.")
    return redirect('schedule')

@login_required(login_url='/dang-nhap/')
def checkout_plan(request, plan_id):
    member = get_object_or_404(Member, user=request.user)
    plan = get_object_or_404(MembershipPlan, id=plan_id)
    existing_order = SubscriptionOrder.objects.filter(member=member, status='PENDING').first()
    
    if request.method == 'POST':
        if existing_order:
            existing_order.delete()
        payment_method = request.POST.get('payment_method', 'TRANSFER')
        order = SubscriptionOrder.objects.create(
            member=member, plan=plan, amount=plan.price, payment_method=payment_method, status='PENDING'
        )
        messages.success(request, f"Đã khởi tạo đơn hàng #{order.id}.")
        return render(request, 'quanlygym/checkout_success.html', {'order': order, 'member': member})
    if existing_order:
        messages.warning(request, "Lưu ý: Xác nhận thanh toán gói này sẽ tự động hủy yêu cầu cũ của bạn.")
    return render(request, 'quanlygym/checkout.html', {'plan': plan, 'member': member})

# ---------------------------------------------------------
# NGHIỆP VỤ 2: KIỂM SOÁT CỬA RA VÀO (CHECK-IN)
# ---------------------------------------------------------
@login_required(login_url='/dang-nhap/')
def simulate_checkin(request):
    member = get_object_or_404(Member, user=request.user)
    
    # CHẶN: Không có thẻ active thì không được vào Gym
    if not member.is_active:
        messages.error(request, "⛔ TỪ CHỐI VÀO CỬA: Thẻ của bạn đã hết hạn hoặc chưa kích hoạt!")
        return redirect('packages')

    default_branch = member.branch or Branch.objects.first()
    if not default_branch:
        messages.error(request, "Hệ thống chưa có dữ liệu chi nhánh!")
        return redirect('profile')
        
    CheckInLog.objects.create(member=member, branch=default_branch)
    messages.success(request, f"✅ Cửa mở! Quét thẻ thành công tại {default_branch.name}. Chúc bạn tập luyện vui vẻ!")
    return redirect('profile')

@login_required(login_url='/dang-nhap/')
def user_profile(request):
    member = Member.objects.filter(user=request.user).first()
    if request.method == 'POST' and member:
        health_form = HealthRecordForm(request.POST)
        if health_form.is_valid():
            record = health_form.save(commit=False)
            record.member = member
            record.save()
            messages.success(request, "Cập nhật chỉ số cơ thể thành công!")
            return redirect('profile')
    else:
        health_form = HealthRecordForm()

    user_classes = ClassEnrollment.objects.filter(member=member) if member else []
    checkin_logs = CheckInLog.objects.filter(member=member).order_by('-checkin_time')[:10] if member else []
    orders = SubscriptionOrder.objects.filter(member=member).order_by('-created_at') if member else []

    context = {'member': member, 'health_form': health_form, 'user_classes': user_classes, 'checkin_logs': checkin_logs, 'orders': orders}
    return render(request, 'quanlygym/profile.html', context)

def booking_view(request):
    initial_data = {}
    if request.user.is_authenticated:
        member = Member.objects.filter(user=request.user).first()
        initial_data = {'full_name': request.user.get_full_name() or request.user.username, 'email': request.user.email, 'phone': member.phone if member else ''}

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Yêu cầu đặt lịch đã gửi thành công!")
            return redirect('booking')
    else:
        form = BookingForm(initial=initial_data)
    return render(request, 'quanlygym/booking.html', {'form': form})

def feedback_view(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            if request.user.is_authenticated:
                fb.user = request.user
            fb.save()
            messages.success(request, "Đã ghi nhận đánh giá của bạn!")
            return redirect('feedback')
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data['name'] = request.user.get_full_name() or request.user.username
        form = FeedbackForm(initial=initial_data)
    feedbacks = Feedback.objects.filter(is_approved=True).order_by('-created_at')
    return render(request, 'quanlygym/feedback.html', {'form': form, 'feedbacks': feedbacks})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Đăng ký tài khoản thành công! Bạn có thể chọn mua gói tập ngay bây giờ.")
            return redirect('packages') 
    else:
        form = RegisterForm()
    return render(request, 'quanlygym/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('profile')
    else:
        form = AuthenticationForm()
    return render(request, 'quanlygym/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

# ==========================================
# CÁC HÀM QUẢN TRỊ (CUSTOM ADMIN)
# ==========================================

@staff_member_required(login_url='/dang-nhap/')
def staff_dashboard(request):
    total_members = Member.objects.count()
    total_revenue = SubscriptionOrder.objects.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0
    pending_orders = SubscriptionOrder.objects.filter(status='PENDING').order_by('-created_at')[:5]
    pending_bookings = Booking.objects.filter(status='PENDING').order_by('-created_at')[:5]
    context = {'total_members': total_members, 'total_revenue': total_revenue, 'pending_orders': pending_orders, 'pending_bookings': pending_bookings}
    return render(request, 'quanlygym/staff_dashboard.html', context)

# ---------------------------------------------------------
# NGHIỆP VỤ 3: TỰ ĐỘNG DỌN RÁC SAU KHI DUYỆT ĐƠN
# ---------------------------------------------------------
@staff_member_required(login_url='/dang-nhap/')
def admin_approve_order(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(SubscriptionOrder, id=order_id)
        if order.status == 'PENDING':
            order.status = 'PAID'
            order.save()
            
            member = order.member
            plan_days = order.plan.duration_days
            
            # Cộng ngày
            if not member.expire_date or member.expire_date < date.today():
                member.expire_date = date.today() + timedelta(days=plan_days)
            else:
                member.expire_date = member.expire_date + timedelta(days=plan_days)
                
            member.membership_type = 'VIP' if 'VIP' in order.plan.name.upper() else 'STD'
            member.save()
            
            # Tự động hủy các đơn PENDING rác khác của user này để tránh lặp bill
            SubscriptionOrder.objects.filter(member=member, status='PENDING').update(status='CANCELLED')

            messages.success(request, f"✅ Đã duyệt đơn #{order.id} và cộng {plan_days} ngày tập cho {member.user.username}!")
        else:
            messages.error(request, "⚠️ Đơn hàng này đã được xử lý trước đó.")
    return redirect('staff_dashboard')

@staff_member_required(login_url='/dang-nhap/')
def admin_approve_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)
        if booking.status == 'PENDING':
            booking.status = 'CONFIRMED'
            booking.save()
            messages.success(request, f"✅ Đã xác nhận lịch hẹn cho: {booking.full_name}!")
    return redirect('staff_dashboard')

@staff_member_required(login_url='/dang-nhap/')
def admin_plan_list(request):
    plans = MembershipPlan.objects.all().order_by('-id')
    return render(request, 'quanlygym/admin_plan_list.html', {'plans': plans})

@staff_member_required(login_url='/dang-nhap/')
def admin_plan_add(request):
    if request.method == 'POST':
        form = MembershipPlanForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thêm gói tập mới thành công!")
            return redirect('admin_plan_list')
    else:
        form = MembershipPlanForm()
    return render(request, 'quanlygym/admin_form.html', {'form': form, 'title': 'Thêm Gói Tập Mới'})

@staff_member_required(login_url='/dang-nhap/')
def admin_plan_edit(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)
    if request.method == 'POST':
        form = MembershipPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cập nhật thành công!")
            return redirect('admin_plan_list')
    else:
        form = MembershipPlanForm(instance=plan)
    return render(request, 'quanlygym/admin_form.html', {'form': form, 'title': f'Sửa Gói Tập: {plan.name}'})

@staff_member_required(login_url='/dang-nhap/')
def admin_plan_delete(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)
    if request.method == 'POST':
        plan.delete()
        messages.warning(request, "Đã xóa gói tập.")
        return redirect('admin_plan_list')
    return render(request, 'quanlygym/admin_plan_confirm_delete.html', {'plan': plan})

@staff_member_required(login_url='/dang-nhap/')
def admin_trainer_list(request):
    trainers = Trainer.objects.all().order_by('-id')
    return render(request, 'quanlygym/admin_trainer_list.html', {'trainers': trainers})

@staff_member_required(login_url='/dang-nhap/')
def admin_trainer_add(request):
    if request.method == 'POST':
        form = TrainerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thêm HLV mới thành công!")
            return redirect('admin_trainer_list')
    else:
        form = TrainerForm()
    return render(request, 'quanlygym/admin_form.html', {'form': form, 'title': 'Thêm Huấn Luyện Viên'})

@staff_member_required(login_url='/dang-nhap/')
def admin_trainer_edit(request, trainer_id):
    trainer = get_object_or_404(Trainer, id=trainer_id)
    if request.method == 'POST':
        form = TrainerForm(request.POST, instance=trainer)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật HLV!")
            return redirect('admin_trainer_list')
    else:
        form = TrainerForm(instance=trainer)
    return render(request, 'quanlygym/admin_form.html', {'form': form, 'title': f'Sửa HLV: {trainer.name}'})

@staff_member_required(login_url='/dang-nhap/')
def admin_trainer_delete(request, trainer_id):
    trainer = get_object_or_404(Trainer, id=trainer_id)
    trainer.delete()
    messages.warning(request, "Đã xóa HLV.")
    return redirect('admin_trainer_list')

@staff_member_required(login_url='/dang-nhap/')
def admin_member_list(request):
    members = Member.objects.all().order_by('-id')
    return render(request, 'quanlygym/admin_member_list.html', {'members': members})

@staff_member_required(login_url='/dang-nhap/')
def admin_member_delete(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    member.user.delete() 
    messages.warning(request, "Đã xóa Hội viên.")
    return redirect('admin_member_list')

@staff_member_required(login_url='/dang-nhap/')
def admin_approve_member_quick(request, member_id):
    if request.method == 'POST':
        member = get_object_or_404(Member, id=member_id)
        if not member.expire_date or member.expire_date < date.today():
            member.expire_date = date.today() + timedelta(days=30)
        else:
            member.expire_date = member.expire_date + timedelta(days=30)
        member.save()
        messages.success(request, f"✅ Đã duyệt và kích hoạt gói 30 ngày cho {member.user.username}!")
    return redirect('admin_member_list')

@staff_member_required(login_url='/dang-nhap/')
def admin_cancel_member_plan(request, member_id):
    if request.method == 'POST':
        member = get_object_or_404(Member, id=member_id)
        member.expire_date = None
        member.membership_type = 'STD'
        member.save()
        messages.warning(request, f"🚫 Đã HỦY gói tập của hội viên {member.user.username}.")
    return redirect('admin_member_list')

@staff_member_required(login_url='/dang-nhap/')
def admin_branch_list(request):
    branches = Branch.objects.all().order_by('-id')
    return render(request, 'quanlygym/admin_branch_list.html', {'branches': branches})

@staff_member_required(login_url='/dang-nhap/')
def admin_branch_add(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm Chi nhánh mới!")
            return redirect('admin_branch_list')
    else:
        form = BranchForm()
    return render(request, 'quanlygym/admin_form.html', {'form': form, 'title': 'Thêm Chi Nhánh Mới'})

@staff_member_required(login_url='/dang-nhap/')
def admin_branch_edit(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật Chi nhánh!")
            return redirect('admin_branch_list')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'quanlygym/admin_form.html', {'form': form, 'title': f'Sửa Chi Nhánh: {branch.name}'})

@staff_member_required(login_url='/dang-nhap/')
def admin_branch_delete(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    branch.delete()
    messages.warning(request, "Đã xóa Chi nhánh!")
    return redirect('admin_branch_list')

@staff_member_required(login_url='/dang-nhap/')
def admin_class_list(request):
    classes = GymClass.objects.all().order_by('day_of_week', 'start_time')
    return render(request, 'quanlygym/admin_class_list.html', {'classes': classes})

@staff_member_required(login_url='/dang-nhap/')
def admin_class_add(request):
    if request.method == 'POST':
        form = GymClassForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm Lịch học mới!")
            return redirect('admin_class_list')
    else:
        form = GymClassForm()
    return render(request, 'quanlygym/admin_form.html', {'form': form, 'title': 'Thêm Lịch Học GroupX'})

@staff_member_required(login_url='/dang-nhap/')
def admin_class_edit(request, class_id):
    gym_class = get_object_or_404(GymClass, id=class_id)
    if request.method == 'POST':
        form = GymClassForm(request.POST, instance=gym_class)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật Lịch học!")
            return redirect('admin_class_list')
    else:
        form = GymClassForm(instance=gym_class)
    return render(request, 'quanlygym/admin_form.html', {'form': form, 'title': f'Sửa Lịch Học: {gym_class.title}'})

@staff_member_required(login_url='/dang-nhap/')
def admin_class_delete(request, class_id):
    gym_class = get_object_or_404(GymClass, id=class_id)
    gym_class.delete()
    messages.warning(request, "Đã xóa Lịch học!")
    return redirect('admin_class_list')