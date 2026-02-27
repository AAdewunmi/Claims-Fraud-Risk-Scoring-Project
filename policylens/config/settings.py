# path: policylens/config/settings.py
"""
Django settings for PolicyLens.

Sprint 5 adds ops app and static files wiring.
"""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_SECRET_KEY=(str, ""),
    DJANGO_ALLOWED_HOSTS=(str, "localhost,127.0.0.1"),
    DATABASE_URL=(str, ""),
    ML_ACTIVE_MODEL_VERSION=(str, "v1_2026_01_13"),
    ML_SCORE_THRESHOLD=(float, 0.6),
    ML_ARTIFACT_DIR=(str, ""),
)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY is required. Set it in .env or environment variables.")

DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "policylens.apps.core",
    "policylens.apps.claims",
    "policylens.apps.ops",
    "policylens.apps.public",
    "policylens.apps.customer",
]

# TODO(accounts): remove this guard once the accounts app ships.
if find_spec("policylens.apps.accounts") is not None:
    INSTALLED_APPS.append("policylens.apps.accounts")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "policylens.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "policylens.config.wsgi.application"
ASGI_APPLICATION = "policylens.config.asgi.application"

DATABASES = {
    "default": env.db(),
}
DATABASES["default"]["CONN_MAX_AGE"] = 60

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "apps" / "ops" / "static",
]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR.parent / "media"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# ML configuration
ML_ACTIVE_MODEL_VERSION = env("ML_ACTIVE_MODEL_VERSION")
ML_SCORE_THRESHOLD = float(env("ML_SCORE_THRESHOLD"))
UI_PAGE_SIZE = 15

_ml_dir = env("ML_ARTIFACT_DIR")
ML_ARTIFACT_DIR = _ml_dir if _ml_dir else str(BASE_DIR.parent / "artifacts" / "ml")

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/ops/"
