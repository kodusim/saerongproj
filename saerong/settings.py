from pathlib import Path
import sys
from django.core.exceptions import ImproperlyConfigured
import environ
Env = environ.Env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = Env()
 
ENV_PATH = env.str("ENV_PATH", default=str(BASE_DIR / ".env"))
env_path = Path(ENV_PATH)
if env_path.exists():
    with env_path.open(encoding="utf-8") as f:
        env.read_env(f, overwrite=True)
else:
    print("not found:", ENV_PATH, file=sys.stderr)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str(
    "SECRET_KEY",
    default="django-insecure-dn^kymsy5h(e&jtgba0r#jh1v6!9gao1e2#g!5#76b)5=dh2s)",
 )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = [
    'localhost', 
    '127.0.0.1', 
    '43.200.27.174',  # 서버 IP 
    'saerong.com', 
    'www.saerong.com'  # www 도메인 추가
]
COMPONENTS = {
     # 0.67 미만 버전과 동일한 동작을 맞추기 위한 설정 (강의에서는 0.61 버전)
     "slot_context_behavior": "allow_override",  # 디폴트: "prefer_root"
 }


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # thrid apps
    "crispy_forms",
    "crispy_bootstrap5",
    "django_components",
    "django_extensions",
    "template_partials",
    "django_htmx",
    # local apps
    "accounts",
    "core",
    "psychotest",
]

if DEBUG:
    INSTALLED_APPS += [
        "debug_toolbar",
    ]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

if DEBUG:
    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    ] + MIDDLEWARE

ROOT_URLCONF = "saerong.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "core" / "src-django-components",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "saerong.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'saerong',
        'USER': 'saerong_user',
        'PASSWORD': '16qjsqkqh16*',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

AUTH_USER_MODEL = "accounts.User"

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = env.str("LANGUAGE_CODE", default="ko-kr")

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "core" / "src-django-components",
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"



 # django-debug-toolbar
 # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html

# django-components
 #  - context variable를 resolve하는 방식이 변경
 #    https://github.com/EmilStenstrom/django-components/?tab=readme-ov-file#isolate-components-slots


INTERNAL_IPS = env.list("INTERNAL_IPS", default=["127.0.0.1"])

# django-crispy-forms
 
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
 
CRISPY_TEMPLATE_PACK = "bootstrap5"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

# 기존
CSP_FRAME_ANCESTORS = env.list("CSP_FRAME_ANCESTORS", default=[])
CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'"] + CSP_FRAME_ANCESTORS
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'"] + CSP_FRAME_ANCESTORS
CSP_IMG_SRC = ["'self'", "data:"] + CSP_FRAME_ANCESTORS

# 추가
if not CSP_FRAME_ANCESTORS:
    CSP_FRAME_ANCESTORS = ["'self'"]