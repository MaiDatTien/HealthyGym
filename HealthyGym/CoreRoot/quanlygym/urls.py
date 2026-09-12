from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('gioi-thieu/', views.intro, name='intro'),
    path('chi-nhanh/', views.branches_view, name='branches'),
    path('co-so-vat-chat/', views.facilities_view, name='facilities'),
    path('lich-hoc/', views.schedule_view, name='schedule'),
    path('dang-ky-lop/<int:class_id>/', views.enroll_class, name='enroll_class'),
    path('huy-lop/<int:class_id>/', views.cancel_enrollment, name='cancel_enrollment'),
    path('tin-tuc/', views.news_list_view, name='news_list'),
    path('tin-tuc/<int:pk>/', views.news_detail_view, name='news_detail'),
    path('bang-gia/', views.packages, name='packages'),
    path('thanh-toan/<int:plan_id>/', views.checkout_plan, name='checkout'),
    path('diem-danh-gia-lap/', views.simulate_checkin, name='simulate_checkin'),
    path('huan-luyen-vien/', views.trainers_view, name='trainers'),
    path('hoi-dap/', views.faq_view, name='faq'),
    path('dat-lich/', views.booking_view, name='booking'),
    path('danh-gia/', views.feedback_view, name='feedback'),
    path('quan-tri/', views.staff_dashboard, name='staff_dashboard'),
    
    path('ho-so/', views.user_profile, name='profile'),
    path('dang-ky/', views.register_view, name='register'),
    path('dang-nhap/', views.login_view, name='login'),
    path('dang-xuat/', views.logout_view, name='logout'),
    
    # ===== CUSTOM ADMIN MODULES =====
    
    path('quan-tri/duyet-don/<int:order_id>/', views.admin_approve_order, name='admin_approve_order'),
    path('quan-tri/duyet-lich/<int:booking_id>/', views.admin_approve_booking, name='admin_approve_booking'),

    path('quan-tri/san-pham/', views.admin_plan_list, name='admin_plan_list'),
    path('quan-tri/san-pham/them/', views.admin_plan_add, name='admin_plan_add'),
    path('quan-tri/san-pham/sua/<int:plan_id>/', views.admin_plan_edit, name='admin_plan_edit'),
    path('quan-tri/san-pham/xoa/<int:plan_id>/', views.admin_plan_delete, name='admin_plan_delete'),

    path('quan-tri/hlv/', views.admin_trainer_list, name='admin_trainer_list'),
    path('quan-tri/hlv/them/', views.admin_trainer_add, name='admin_trainer_add'),
    path('quan-tri/hlv/sua/<int:trainer_id>/', views.admin_trainer_edit, name='admin_trainer_edit'),
    path('quan-tri/hlv/xoa/<int:trainer_id>/', views.admin_trainer_delete, name='admin_trainer_delete'),

    path('quan-tri/hoi-vien/', views.admin_member_list, name='admin_member_list'),
    path('quan-tri/hoi-vien/xoa/<int:member_id>/', views.admin_member_delete, name='admin_member_delete'),
    path('quan-tri/hoi-vien/duyet/<int:member_id>/', views.admin_approve_member_quick, name='admin_approve_member_quick'),
    path('quan-tri/hoi-vien/huy-goi/<int:member_id>/', views.admin_cancel_member_plan, name='admin_cancel_member_plan'),
    
    # CHI NHÁNH & LỊCH HỌC BỔ SUNG
    path('quan-tri/chi-nhanh/', views.admin_branch_list, name='admin_branch_list'),
    path('quan-tri/chi-nhanh/them/', views.admin_branch_add, name='admin_branch_add'),
    path('quan-tri/chi-nhanh/sua/<int:branch_id>/', views.admin_branch_edit, name='admin_branch_edit'),
    path('quan-tri/chi-nhanh/xoa/<int:branch_id>/', views.admin_branch_delete, name='admin_branch_delete'),

    path('quan-tri/lich-hoc/', views.admin_class_list, name='admin_class_list'),
    path('quan-tri/lich-hoc/them/', views.admin_class_add, name='admin_class_add'),
    path('quan-tri/lich-hoc/sua/<int:class_id>/', views.admin_class_edit, name='admin_class_edit'),
    path('quan-tri/lich-hoc/xoa/<int:class_id>/', views.admin_class_delete, name='admin_class_delete'),
]