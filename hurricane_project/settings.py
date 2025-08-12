"""
Django settings for hurricane_project project.
"""

from pathlib import Path
import os

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Core security / env flags (Render-friendly) ---
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-unsafe")
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

# Allowed hosts (comma-separated env supported)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,.onrender.com"
).split(",") if h.strip()]

# Tell Django requests are HTTPS when behind Render's proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF (trust Render; allow overrides via env)
CSRF_TRUSTED_ORIGINS = [
    *[o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()],
    "https://*.onrender.com",
]

# Extra hardening in production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 60  # 60 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- Installed apps ---
INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",  # let WhiteNoise handle static in dev, too
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tracker",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # must be right after SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hurricane_project.urls"

# --- Templates ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # safe even if folder doesn't exist
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hurricane_project.wsgi.application"

# --- Database (SQLite, rebuilt from CSV at boot) ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --- Password validators ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n / tz ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"  # adjust if you prefer UTC
USE_I18N = True
USE_TZ = True

# --- Static files (WhiteNoise) ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic target

# Only include app static dir if it exists (prevents errors)
STATICFILES_DIRS = [p for p in [BASE_DIR / "tracker" / "static"] if p.exists()]

# Django 5 storage-style config for WhiteNoise
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }
}

# --- Misc ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
