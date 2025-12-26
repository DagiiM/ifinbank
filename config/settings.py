"""
Django settings for iFin Bank Verification System.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-ifinbank-dev-key-change-in-production-83egh_jyij5pa'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Project apps
    'apps.core',
    'apps.accounts',
    'apps.verification',
    'apps.documents',
    'apps.compliance',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Custom User Model
AUTH_USER_MODEL = 'accounts.User'


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Login URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'verification:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'


# =============================================================================
# AI Services Configuration
# =============================================================================

# vLLM Server Configuration
# Reference: https://github.com/vllm-project/vllm
VLLM_API_URL = os.environ.get('VLLM_API_URL', 'http://localhost:8000')
VLLM_API_KEY = os.environ.get('VLLM_API_KEY', '')
VLLM_MODEL_NAME = os.environ.get('VLLM_MODEL_NAME', 'deepseek-ai/DeepSeek-OCR')
VLLM_TIMEOUT = int(os.environ.get('VLLM_TIMEOUT', '120'))
VLLM_MAX_TOKENS = int(os.environ.get('VLLM_MAX_TOKENS', '8192'))

# DeepSeek-OCR Configuration
# Reference: https://github.com/deepseek-ai/DeepSeek-OCR
# Supported modes: free_ocr, document, figure, describe, locate
DEEPSEEK_OCR_MODE = os.environ.get('DEEPSEEK_OCR_MODE', 'document')
DEEPSEEK_OCR_BASE_SIZE = int(os.environ.get('DEEPSEEK_OCR_BASE_SIZE', '1024'))
DEEPSEEK_OCR_IMAGE_SIZE = int(os.environ.get('DEEPSEEK_OCR_IMAGE_SIZE', '640'))

# ChromaDB Configuration
# Reference: https://www.trychroma.com/
CHROMADB_HOST = os.environ.get('CHROMADB_HOST', 'localhost')
CHROMADB_PORT = int(os.environ.get('CHROMADB_PORT', '8000'))
CHROMADB_COLLECTION = os.environ.get('CHROMADB_COLLECTION', 'ifinbank_policies')
CHROMADB_PERSIST_DIR = BASE_DIR / 'chromadb_data'

# Embedding Model
EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

# Legacy OCR Service (fallback)
OCR_API_URL = os.environ.get('OCR_API_URL', 'http://localhost:8080')
OCR_API_KEY = os.environ.get('OCR_API_KEY', '')

# Feature Flags
USE_VLLM_OCR = os.environ.get('USE_VLLM_OCR', 'True').lower() == 'true'
USE_CHROMADB = os.environ.get('USE_CHROMADB', 'True').lower() == 'true'

# Verification Thresholds
VERIFICATION_AUTO_APPROVE_THRESHOLD = float(os.environ.get('VERIFICATION_AUTO_APPROVE', '85.0'))
VERIFICATION_REVIEW_THRESHOLD = float(os.environ.get('VERIFICATION_REVIEW', '70.0'))
VERIFICATION_AUTO_REJECT_THRESHOLD = float(os.environ.get('VERIFICATION_AUTO_REJECT', '50.0'))


# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'ifinbank.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Create logs directory if it doesn't exist
(BASE_DIR / 'logs').mkdir(exist_ok=True)
