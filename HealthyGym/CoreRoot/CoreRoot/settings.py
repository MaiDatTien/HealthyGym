"""
Django settings for CoreRoot project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = 'django-insecure-c408#oeg#4vi8$m8src89iaahzv-#g&0z$@5se8^xn$akj^%eh'

DEBUG = True

ALLOWED_HOSTS = []


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [

    # Django built-in applications
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Hỗ trợ format số tiền
    'django.contrib.humanize',

    # Thư viện hỗ trợ
    'rest_framework',
    'corsheaders',

    # Application của đồ án
    'quanlygym',
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    # CORS - có thể giữ lại nếu sau này cần API
    'corsheaders.middleware.CorsMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = 'CoreRoot.urls'


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        # Có thể thêm thư mục templates chung tại đây nếu cần
        'DIRS': [
            BASE_DIR / 'templates',
        ],

        'APP_DIRS': True,

        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ============================================================
# WSGI
# ============================================================

WSGI_APPLICATION = 'CoreRoot.wsgi.application'


# ============================================================
# DATABASE - POSTGRESQL
# ============================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'quanlygym_db',
        'USER': 'postgres',
        'PASSWORD': '123',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = 'vi'

TIME_ZONE = 'Asia/Ho_Chi_Minh'

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]


# ============================================================
# MEDIA FILES
# ============================================================

# Dùng cho upload ảnh hội viên, HLV, bài tập...
MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================
# LOGIN / LOGOUT
# ============================================================

# Khi người dùng chưa đăng nhập
LOGIN_URL = 'login'

# Sau khi đăng nhập thành công
LOGIN_REDIRECT_URL = 'home'

# Sau khi đăng xuất
LOGOUT_REDIRECT_URL = 'home'


# ============================================================
# EMAIL
# ============================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'sandbox.smtp.mailtrap.io'

EMAIL_HOST_USER = 'add922be1abe79'

EMAIL_HOST_PASSWORD = '112bc97d7042a4'

EMAIL_PORT = 2525

EMAIL_USE_TLS = True

EMAIL_USE_SSL = False


# ============================================================
# REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}


# ============================================================
# CORS
# ============================================================

# Hiện tại bạn không dùng React nên phần này chưa thực sự cần.
# Giữ lại để sau này nếu xây API/frontend riêng thì có thể sử dụng.

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]


# ============================================================
# DEVELOPMENT
# ============================================================

# Cho phép Django phục vụ media trong môi trường development.
# Phần này còn cần cấu hình thêm trong urls.py.