"""
Django settings for Phoenix Scientific Platform
"""

import logging
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try to load from parent directory if .env is not in backend root
    load_dotenv(BASE_DIR.parent / '.env')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# SECURITY WARNING: keep the secret key used in production secret! Never commit real keys.
_secret = (os.getenv('SECRET_KEY') or '').strip()
if _secret:
    SECRET_KEY = _secret
elif DEBUG:
    SECRET_KEY = 'django-insecure-dev-only-not-for-production'
else:
    raise ImproperlyConfigured('SECRET_KEY must be set in the environment when DEBUG=False')

# Productionda tez-tez: .env da faqat ilmiyfaoliyat.uz bo'lib, api.ilmiyfaoliyat.uz qolib ketadi → 400 Bad Request.
_DEFAULT_ALLOWED_HOSTS = (
    'api.ilmiyfaoliyat.uz,ilmiyfaoliyat.uz,www.ilmiyfaoliyat.uz,167.71.53.238,localhost,127.0.0.1'
)


def _normalize_allowed_host_entry(raw: str) -> str:
    """.env da https://, bo'sh joy, port qo'shimchalari bo'lsa ham tozalaymiz."""
    h = (raw or '').strip().strip('"').strip("'")
    if not h:
        return ''
    h = h.lower()
    if '://' in h:
        h = h.split('://', 1)[1]
    h = h.split('/')[0].split('@')[-1]
    # domen:443 — Django ba'zan Host sarlavhasida port bilan tekshiradi
    if h.count(':') == 1 and not h.startswith('['):
        host_part, port_part = h.rsplit(':', 1)
        if port_part.isdigit():
            h = host_part
    return h.strip()


_raw_allowed = (os.getenv('ALLOWED_HOSTS') or '').strip()
_base = _raw_allowed if _raw_allowed else _DEFAULT_ALLOWED_HOSTS
ALLOWED_HOSTS = []
for part in _base.split(','):
    n = _normalize_allowed_host_entry(part)
    if n and n not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(n)
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = [
        _normalize_allowed_host_entry(p)
        for p in _DEFAULT_ALLOWED_HOSTS.split(',')
        if _normalize_allowed_host_entry(p)
    ]
# api subdomain har doim (DEBUG ham) — brauzer / nginx orqali kelganda 400 bo'lmasin
if '*' not in ALLOWED_HOSTS and 'api.ilmiyfaoliyat.uz' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('api.ilmiyfaoliyat.uz')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    # 'django_cleanup',  # Uncomment after installing: pip install django-cleanup
    
    # Local apps
    'apps.users',
    'apps.articles',
    'apps.journals',
    'apps.payments',
    'apps.translations',
    'apps.reviews',
    'apps.notifications',
    'apps.udc',
]

# CorsMiddleware must be as high as possible (before WhiteNoise / CommonMiddleware) so
# OPTIONS preflight and API responses always get CORS headers from django-cors-headers.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'config.monitoring_middleware.RequestMonitoringMiddleware',
    'config.middleware.AdminLoginRateLimitMiddleware',
    'config.middleware.ApiSecurityHeadersMiddleware',
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
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'phoenix_scientific'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Fallback to SQLite for development
if os.getenv('USE_SQLITE', 'False').lower() in ('true', '1', 't'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'config.authentication.CookieAwareJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.PhoenixPageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('THROTTLE_ANON', '120/minute'),
        'user': os.getenv('THROTTLE_USER', '600/minute'),
        'auth': os.getenv('THROTTLE_AUTH', '20/minute'),
        'gemini': os.getenv('THROTTLE_GEMINI', '40/hour'),
    },
}

# JWT — productionda JWT_ACCESS_MINUTES / JWT_REFRESH_DAYS bilan qisqartirish mumkin
_jwt_access_minutes = int(os.getenv('JWT_ACCESS_MINUTES', '1440'))  # default 24 soat
_jwt_refresh_days = int(os.getenv('JWT_REFRESH_DAYS', '7'))

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=max(5, min(_jwt_access_minutes, 60 * 24 * 30))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=max(1, min(_jwt_refresh_days, 365))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# HttpOnly JWT cookies (same-site SPA → API); JSON body tokens ham qoladi (SPA mosligi)
JWT_USE_HTTPONLY_COOKIES = os.getenv('JWT_USE_HTTPONLY_COOKIES', str(not DEBUG)).lower() in (
    'true',
    '1',
    'yes',
    'on',
)
JWT_ACCESS_COOKIE_NAME = os.getenv('JWT_ACCESS_COOKIE_NAME', 'access').strip() or 'access'
JWT_REFRESH_COOKIE_NAME = os.getenv('JWT_REFRESH_COOKIE_NAME', 'refresh').strip() or 'refresh'
JWT_COOKIE_DOMAIN = os.getenv('JWT_AUTH_COOKIE_DOMAIN', '').strip() or None
JWT_RETURN_TOKENS_IN_JSON = os.getenv('JWT_RETURN_TOKENS_IN_JSON', 'true').lower() in ('true', '1', 'yes', 'on')

# Admin login: attempts per IP per window (middleware)
ADMIN_LOGIN_RATELIMIT_PER_IP = int(os.getenv('ADMIN_LOGIN_RATELIMIT_PER_IP', '30'))
ADMIN_LOGIN_RATELIMIT_WINDOW_SEC = int(os.getenv('ADMIN_LOGIN_RATELIMIT_WINDOW_SEC', '900'))

# Optional CSP for API responses (bo'sh = yuborilmasin)
DJANGO_API_CSP = os.getenv('DJANGO_API_CSP', '').strip()

# Request monitoring (JSON log — Loki / ELK uchun qulay)
MONITORING_LOG_REQUESTS = os.getenv('MONITORING_LOG_REQUESTS', 'true').lower() in (
    'true',
    '1',
    'yes',
    'on',
)
MONITORING_LOG_JSON = os.getenv('MONITORING_LOG_JSON', 'false').lower() in ('true', '1', 'yes', 'on')

# CORS Settings
# Explicitly check for 'True' string (case-insensitive) - default to False for production
# IMPORTANT: Start with False, only set to True if explicitly 'true'
cors_allow_all_env_raw = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False')
cors_allow_all_env = cors_allow_all_env_raw.strip() if cors_allow_all_env_raw else 'False'
cors_allow_all_lower = cors_allow_all_env.lower() if cors_allow_all_env else 'false'

# Default to False - only set to True if explicitly 'true', '1', 'yes', or 'on'
CORS_ALLOW_ALL_ORIGINS = False
if cors_allow_all_lower in ('true', '1', 'yes', 'on'):
    CORS_ALLOW_ALL_ORIGINS = True

# Clean CORS_ALLOWED_ORIGINS - remove spaces and filter empty strings
# Production origins
cors_origins_env = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'https://ilmiyfaoliyat.uz,https://www.ilmiyfaoliyat.uz,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173',
)
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]

# Ensure production origins are always included (www and apex)
for _origin in ('https://ilmiyfaoliyat.uz', 'https://www.ilmiyfaoliyat.uz'):
    if _origin not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(_origin)

# Regex fallback: production .env often lists only dev origins; without this, SPA login preflight fails
# (verified: OPTIONS with Origin https://ilmiyfaoliyat.uz had no Allow-Origin while localhost:5173 did).
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://ilmiyfaoliyat\.uz$',
    r'^https://www\.ilmiyfaoliyat\.uz$',
]

# If CORS_ALLOW_ALL_ORIGINS is True, clear CORS_ALLOWED_ORIGINS (django-cors-headers behavior)
if CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = []

# Debug logging (for troubleshooting)
logger = logging.getLogger(__name__)
if not CORS_ALLOW_ALL_ORIGINS:
    logger.info(
        f"CORS settings: ALLOW_ALL=False, ALLOWED_ORIGINS={CORS_ALLOWED_ORIGINS}, "
        f"REGEXES={len(CORS_ALLOWED_ORIGIN_REGEXES)} pattern(s), ENV_VALUE={cors_allow_all_env}"
    )
else:
    logger.warning(f"CORS_ALLOW_ALL_ORIGINS is True! This should be False in production. ENV_VALUE={cors_allow_all_env}")

CORS_ALLOW_CREDENTIALS = True

# Frontend base URL (for Click return_url after payment)
FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000').rstrip('/')

CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-api-key',
    # SPA apiFetch har so'rovda X-Request-ID yuboradi — preflight'da ruxsat bo'lmasa CORS "bloklandi"
    'x-request-id',
]

CORS_PREFLIGHT_MAX_AGE = 3600
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken', 'X-Request-ID']

# CSRF (SessionMiddleware + HTTPS) — frontend domenlari; API boshqa dasturlarga tegmaydi
_csrf_trusted = os.getenv('CSRF_TRUSTED_ORIGINS', '').strip()
if _csrf_trusted:
    CSRF_TRUSTED_ORIGINS = [x.strip() for x in _csrf_trusted.split(',') if x.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://ilmiyfaoliyat.uz',
        'https://www.ilmiyfaoliyat.uz',
        'https://api.ilmiyfaoliyat.uz',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ]

# File Upload Settings
_upload_mb = max(1, min(int(os.getenv('MAX_UPLOAD_MB', '10')), 100))
FILE_UPLOAD_MAX_MEMORY_SIZE = _upload_mb * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = _upload_mb * 1024 * 1024

# Gemini AI — faqat serverda .env da o'rnating (GitHubga yozmang)
# Bir nechta nomlar bilan kelishi mumkin (legacy): GOOGLE_API_KEY, GENAI_API_KEY
GEMINI_API_KEY = (
    (os.getenv('GEMINI_API_KEY') or '').strip()
    or (os.getenv('GOOGLE_API_KEY') or '').strip()
    or (os.getenv('GENAI_API_KEY') or '').strip()
)

# Gemini model: .env da GEMINI_MODEL (masalan gemini-1.5-flash, gemini-2.0-flash)
GEMINI_MODEL = (os.getenv('GEMINI_MODEL') or 'gemini-1.5-flash').strip()
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv('GEMINI_MAX_OUTPUT_TOKENS', '8192'))
# Antiplagiat promptiga kiritiladigan matn chegarami (belgi)
GEMINI_PLAGIARISM_INPUT_CHARS = int(os.getenv('GEMINI_PLAGIARISM_INPUT_CHARS', '12000'))

# Click API HTTP client
CLICK_HTTP_TIMEOUT_SEC = int(os.getenv('CLICK_HTTP_TIMEOUT_SEC', '45'))

# UDK: to'lov boshqaruvi (False = bepul, darhol bajariladi; True = to'lov kerak)
UDK_PAYMENT_ENABLED = os.getenv('UDK_PAYMENT_ENABLED', 'true').lower() in ('true', '1', 'yes')

# Click Payment Settings — maxfiy kalitlar faqat .env (Gitga yozilmaydi)
CLICK_MERCHANT_ID = os.getenv('CLICK_MERCHANT_ID', '45730')
CLICK_SERVICE_ID = os.getenv('CLICK_SERVICE_ID', '82154')
CLICK_SECRET_KEY = (os.getenv('CLICK_SECRET_KEY') or '').strip()
CLICK_MERCHANT_USER_ID = os.getenv('CLICK_MERCHANT_USER_ID', '63536')

CLICK_SERVICE_82154_SECRET_KEY = (os.getenv('CLICK_SERVICE_82154_SECRET_KEY') or '').strip()
CLICK_SERVICE_82154_MERCHANT_USER_ID = os.getenv('CLICK_SERVICE_82154_MERCHANT_USER_ID', '63536')
CLICK_SERVICE_82155_SECRET_KEY = (os.getenv('CLICK_SERVICE_82155_SECRET_KEY') or '').strip()
CLICK_SERVICE_82155_MERCHANT_USER_ID = os.getenv('CLICK_SERVICE_82155_MERCHANT_USER_ID', '64985')
CLICK_SERVICE_89248_SECRET_KEY = (os.getenv('CLICK_SERVICE_89248_SECRET_KEY') or '').strip()
CLICK_SERVICE_88045_SECRET_KEY = (os.getenv('CLICK_SERVICE_88045_SECRET_KEY') or '').strip()

# Payme Payment Settings
PAYME_MERCHANT_ID = os.getenv('PAYME_MERCHANT_ID', '')
PAYME_MERCHANT_KEY = os.getenv('PAYME_MERCHANT_KEY', '')
PAYME_TEST_KEY = os.getenv('PAYME_TEST_KEY', '')
PAYME_IS_TEST = os.getenv('PAYME_IS_TEST', 'True').lower() == 'true'
PAYME_ENDPOINT = os.getenv('PAYME_ENDPOINT', 'https://checkout.paycom.uz')

# Email Settings (for notifications)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@phoenix-scientific.uz')

# Celery Settings
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Logging — fayl: faqat DJANGO_LOG_TO_FILE=true yoki DEBUG (read-only konteynerlarda xatoliksiz)
_log_env = (os.getenv('DJANGO_LOG_TO_FILE') or '').strip().lower()
if _log_env in ('false', '0', 'no'):
    _use_file_log = False
elif _log_env in ('true', '1', 'yes'):
    _use_file_log = True
else:
    _use_file_log = DEBUG

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'phoenix.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

if _use_file_log:
    try:
        _log_path = BASE_DIR / 'logs'
        _log_path.mkdir(parents=True, exist_ok=True)
        _log_file = _log_path / 'django.log'
        LOGGING['handlers']['file'] = {
            'class': 'logging.FileHandler',
            'filename': str(_log_file),
            'formatter': 'verbose',
        }
        LOGGING['root']['handlers'].append('file')
        LOGGING['loggers']['django']['handlers'].append('file')
    except OSError:
        pass

# Cookie siyosati (SPA + API — SameSite=Lax yetarli)
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# --- Production HTTPS / cookie hardening (nginx TLS orqali) ---
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes', 'on')
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() in ('true', '1', 'yes')
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

if not DEBUG and not CLICK_SECRET_KEY and not any(
    (
        CLICK_SERVICE_82154_SECRET_KEY,
        CLICK_SERVICE_82155_SECRET_KEY,
        CLICK_SERVICE_89248_SECRET_KEY,
        CLICK_SERVICE_88045_SECRET_KEY,
    )
):
    logger.warning(
        'Click secret keys are empty — tolovlar ishlamasligi mumkin. .env da CLICK_SECRET_KEY yoki '
        'CLICK_SERVICE_*_SECRET_KEY ni Click merchant kabinetidan kiriting.'
    )

# GitHub Webhook deploy (boshqa servis — SSH/Actions shart emas). Secret bo‘lmasa URL 404.
GITHUB_DEPLOY_WEBHOOK_SECRET = (os.getenv('GITHUB_DEPLOY_WEBHOOK_SECRET') or '').strip()
GITHUB_DEPLOY_HOOK_BRANCH = (os.getenv('GITHUB_DEPLOY_HOOK_BRANCH') or 'master').strip()
DEPLOY_HOOK_SCRIPT = (os.getenv('DEPLOY_HOOK_SCRIPT') or '/phonix/deploy_phonix.sh').strip()
_github_repos = (os.getenv('GITHUB_DEPLOY_REPO') or 'aiziyrak-coder/phonixB,aiziyrak-coder/phonixF').strip()
GITHUB_DEPLOY_REPOS = frozenset(r.strip() for r in _github_repos.split(',') if r.strip())

def _sentry_before_send(event, hint):
    """Authorization va cookie ma’lumotlarini yubormaslik."""
    try:
        request = event.get('request', {})
        if isinstance(request, dict):
            headers = request.get('headers')
            if isinstance(headers, dict):
                for k in list(headers.keys()):
                    lk = str(k).lower()
                    if lk in ('authorization', 'cookie', 'x-metrics-key', 'x-api-key'):
                        headers[k] = '[Filtered]'
    except Exception:
        pass
    return event


_sentry_dsn = (os.getenv('SENTRY_DSN') or '').strip()
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        _sentry_kwargs = dict(
            dsn=_sentry_dsn,
            integrations=[
                DjangoIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            send_default_pii=False,
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.05')),
            environment=os.getenv('SENTRY_ENVIRONMENT', 'production' if not DEBUG else 'development'),
            release=os.getenv('APP_VERSION') or os.getenv('GIT_REVISION') or None,
            before_send=_sentry_before_send,
        )
        _prof = float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0') or '0')
        if _prof > 0:
            _sentry_kwargs['profiles_sample_rate'] = _prof
        sentry_sdk.init(**_sentry_kwargs)
    except ImportError:
        logger.warning('SENTRY_DSN o‘rnatilgan, lekin sentry-sdk o‘rnatilmagan (pip install sentry-sdk).')
