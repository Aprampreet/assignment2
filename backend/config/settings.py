import os
import re
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
env = os.environ
DEBUG = env.get("DJANGO_DEBUG") == "1"
TESTING = env.get("MEDORA_TESTING") == "1"
SECRET_KEY = env.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY or (not DEBUG and not TESTING and len(SECRET_KEY) < 50):
    raise ImproperlyConfigured("Supply a strong DJANGO_SECRET_KEY.")
ALLOWED_HOSTS = env.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
USE_TZ = True
TIME_ZONE = "UTC"
STATIC_URL = "/static/"
STATIC_ROOT = Path(__file__).resolve().parents[1] / "staticfiles"
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "rest_framework_simplejwt.token_blacklist", "drf_spectacular",
    "accounts", "patients", "doctors", "mappings", "audit", "dashboard", "assistant",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware",
    "config.http.RequestContext",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if not DEBUG:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
    "DIRS": [Path(__file__).resolve().parents[1] / "templates"],
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
schema = env.get("DATABASE_SCHEMA", "medora")
if not re.fullmatch(r"medora(?:_[a-z0-9_]+)?", schema):
    raise ImproperlyConfigured("Use a dedicated medora schema.")
if TESTING:
    url = env.get("TEST_DATABASE_URL", "")
    parsed = urlsplit(url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "db-test"} or parsed.path != "/medora_test":
        raise ImproperlyConfigured("Tests require an isolated local medora_test database.")
    if env.get("DATABASE_URL") and urlsplit(env["DATABASE_URL"]).hostname == parsed.hostname:
        raise ImproperlyConfigured("Test and application database hosts must differ in the test process.")
else:
    if {"test", "flush"}.intersection(sys.argv[1:]):
        raise ImproperlyConfigured("Destructive commands require isolated test settings.")
    database_variable = "DATABASE_URL"
    if "migrate" in sys.argv[1:] and env.get("MIGRATION_DATABASE_URL"):
        database_variable = "MIGRATION_DATABASE_URL"
    url = env.get(database_variable, "").strip()
    if not url:
        raise ImproperlyConfigured(f"{database_variable} is missing from the service environment. Local .env files are not deployed.")
    try:
        parsed_url = urlsplit(url)
        valid_url = (parsed_url.scheme in {"postgres", "postgresql"} and parsed_url.hostname
                     and parsed_url.hostname.endswith((".supabase.co", ".pooler.supabase.com")))
    except ValueError:
        valid_url = False
    if not valid_url:
        raise ImproperlyConfigured(
            f"{database_variable} must contain only a PostgreSQL connection URL from Supabase Connect. "
            "For an IPv4-only host, select Session pooler; do not include the variable name or quotes."
        )
db = dj_database_url.parse(url, conn_max_age=0 if TESTING else 60, conn_health_checks=True)
if db["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("PostgreSQL is required.")
options = {"options": f"-c search_path={schema}"}
if not TESTING:
    options["sslmode"] = "require"
    if env.get("DATABASE_SSL_ROOT_CERT"):
        options.update(sslmode="verify-full", sslrootcert=env["DATABASE_SSL_ROOT_CERT"])
db["OPTIONS"] = options
if TESTING:
    db["TEST"] = {"NAME": "test_medora_test"}
DATABASES = {"default": db}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{name}"}
    for name in ("UserAttributeSimilarityValidator", "MinimumLengthValidator",
                 "CommonPasswordValidator", "NumericPasswordValidator")
]
AUTH_PASSWORD_VALIDATORS[1]["OPTIONS"] = {"min_length": 12}
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.http.api_error",
}
SPECTACULAR_SETTINGS = {"TITLE": "Medora Healthcare DRF API", "VERSION": "1.0.0", "SERVE_INCLUDE_SCHEMA": False}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5), "REFRESH_TOKEN_LIFETIME": timedelta(hours=24),
    "ROTATE_REFRESH_TOKENS": True, "BLACKLIST_AFTER_ROTATION": True, "CHECK_REVOKE_TOKEN": True,
    "SIGNING_KEY": env.get("JWT_SIGNING_KEY") or SECRET_KEY,
}
CACHES = {"default": ({
    "BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": env["REDIS_URL"],
} if env.get("REDIS_URL") else {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "medora",
})}
SECURE_SSL_REDIRECT = not (DEBUG or TESTING)
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT
SECURE_HSTS_SECONDS = 31536000 if SECURE_SSL_REDIRECT else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_SSL_REDIRECT
SECURE_REFERRER_POLICY = "same-origin"
if env.get("TRUST_HTTPS_PROXY") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
