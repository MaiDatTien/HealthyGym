"""
URL configuration for CoreRoot project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Kết nối toàn bộ URL của app quanlygym vào hệ thống chính
    path('', include('quanlygym.urls')), 
]

# Cấu hình để Django có thể hiển thị hình ảnh tải lên (Media) trong lúc Dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)