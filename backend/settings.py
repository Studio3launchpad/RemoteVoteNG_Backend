import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-rvng-secret-key-2026-remotevote-ng-studios')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'cloudinary_storage',
    'cloudinary',
    
    # Local apps
    'api.apps.ApiConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # CorsMiddleware must be placed first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'api.middleware.AuditLogMiddleware',  # Capture active user context for signals
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# If DATABASE_URL is provided (e.g. Postgres in production), switch to it dynamically
# Force SQLite during test runs to keep tests isolated and fast
import sys
if 'test' not in sys.argv:
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        DATABASES['default'] = dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )




# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
MEDIA_URL = '/media/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'api.ElectoralUser'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'api.auth_backend.EVotingAuthBackend',
]

# REST Framework configurations
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication'
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}

# CORS configuration
CORS_ALLOW_ALL_ORIGINS = True  # Allowed for local development/demonstration
# If we want to restrict to specific origins, we can use:
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",
#     "http://localhost:5173",
#     "http://localhost:8080",
# ]

# Brevo configuration settings
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "noreply@remotevoteng.org")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "RemoteVote NG")

# INEC Electoral Settings
# Number of Returning Officer approvals required before an election can be officially closed
ELECTION_CLOSURE_SIGNATURES_REQUIRED = int(os.getenv("ELECTION_CLOSURE_SIGNATURES_REQUIRED", "2"))

# Frontend URL for invitation links (set to frontend dev server by default)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Auto-provisioned INEC Secretary account settings for deployment
SECRETARY_NIN = os.getenv("SECRETARY_NIN", "99999999999")
SECRETARY_STAFF_NUMBER = os.getenv("SECRETARY_STAFF_NUMBER", "STAFF-SECRETARY-2026")
SECRETARY_DEFAULT_PASSWORD = os.getenv("SECRETARY_DEFAULT_PASSWORD", "SecPass2026!")
SECRETARY_EMAIL = os.getenv("SECRETARY_EMAIL", "secretary@remotevoteng.org")
SECRETARY_NAME = os.getenv("SECRETARY_NAME", "INEC Secretary HQ")
SECRETARY_STATE = os.getenv("SECRETARY_STATE", "FCT")
SECRETARY_LGA = os.getenv("SECRETARY_LGA", "Abuja Municipal")

# Cloudinary Storage Configuration
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    'API_KEY': os.getenv("CLOUDINARY_API_KEY", ""),
    'API_SECRET': os.getenv("CLOUDINARY_API_SECRET", "")
}
