# path: policylens/config/settings.py
"""
Django settings for PolicyLens.

Week 7 Day 2 adds production hardening for running behind a reverse proxy (Nginx):
- Secure cookie flags suitable for HTTPS termination
- CSRF trusted origins for deployed hosts
- Proxy header support so Django correctly detects HTTPS and host
"""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
from typing import List, Optional, Tuple

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
    # Reverse proxy and security hardening
    DJANGO_CSRF_TRUSTED_ORIGINS=(str, ""),
    DJANGO_SECURE_PROXY_SSL_HEADER=(bool, True),
    DJANGO_USE_X_FORWARDED_HOST=(bool, True),
    DJANGO_SECURE_SSL_REDIRECT=(bool, False),
    DJANGO_SESSION_COOKIE_SECURE=(bool, True),
    DJANGO_CSRF_COOKIE_SECURE=(bool, True),
    # Optional HSTS controls (off by default because they are domain-level commitments)
    DJANGO_SECURE_HSTS_SECONDS=(int, 0),
    DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, False),
    DJANGO_SECURE_HSTS_PRELOAD=(bool, False),
)

ENV_FILE = BASE_DIR.parent / ".env"
if ENV_FILE.exists():
    # Local dev convenience: allows `python manage.py ...` to work without exporting vars manually.
    env.read_env(str(ENV_FILE))


def _split_csv(value: str) -> List[str]:
    """
    Split a comma-separated string into a clean list, dropping empty parts.

    Args:
        value: CSV string, for example "a,b, c".

    Returns:
        Cleaned list of strings.
    """
    return [part.strip() for part in value.split(",") if part.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY is required. Set it in .env or environment variables.")

DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = _split_csv(env("DJANGO_ALLOWED_HOSTS"))

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

# Optional apps: keep settings resilient while refactors land across sprints.
if find_spec("policylens.apps.accounts") is not None:
    INSTALLED_APPS.append("policylens.apps.accounts")

if find_spec("policylens.apps.console") is not None:
    INSTALLED_APPS.append("policylens.apps.console")

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

# collectstatic target used in production (and in Week 7 entrypoint)
STATIC_ROOT = BASE_DIR.parent / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR.parent / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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

# Auth defaults (multi-surface routing will refine these in the UI wiring issue)
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"

# Production hardening behind Nginx

# Proxy header support:
# - Nginx should set X-Forwarded-Proto: https
# - optionally set X-Forwarded-Host when using a different upstream host header
_secure_proxy_enabled = env("DJANGO_SECURE_PROXY_SSL_HEADER")
SECURE_PROXY_SSL_HEADER: Optional[Tuple[str, str]] = (
    ("HTTP_X_FORWARDED_PROTO", "https") if _secure_proxy_enabled else None
)

USE_X_FORWARDED_HOST = env("DJANGO_USE_X_FORWARDED_HOST")

# CSRF trusted origins must include scheme for Django 4+:
# Example: "https://policylens.example.com,https://www.policylens.example.com"
_csrf_origins_raw = env("DJANGO_CSRF_TRUSTED_ORIGINS")
CSRF_TRUSTED_ORIGINS = _split_csv(_csrf_origins_raw) if _csrf_origins_raw else []

# Secure cookies:
# In production behind HTTPS termination, these should stay True.
# For local testing without TLS, override via environment variables.
SESSION_COOKIE_SECURE = env("DJANGO_SESSION_COOKIE_SECURE") if not DEBUG else False
CSRF_COOKIE_SECURE = env("DJANGO_CSRF_COOKIE_SECURE") if not DEBUG else False

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

# Redirect HTTP to HTTPS (recommended behind TLS termination).
# If your local environment does not serve HTTPS, set DJANGO_SECURE_SSL_REDIRECT=0.
SECURE_SSL_REDIRECT = env("DJANGO_SECURE_SSL_REDIRECT") if not DEBUG else False

# HSTS (optional; enable only when you are confident in your domain and HTTPS setup).
SECURE_HSTS_SECONDS = env("DJANGO_SECURE_HSTS_SECONDS")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env("DJANGO_SECURE_HSTS_PRELOAD")

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
