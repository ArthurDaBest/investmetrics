"""
Django settings for the Investmetrics website and Investmetrics Learning.

The existing corporate website remains the root application. AI at Work is
mounted as a separate Django app under /learn/.
"""

from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent


# -----------------------------------------------------------------------------
# Security / environment
# -----------------------------------------------------------------------------

DEBUG = os.getenv("DEBUG", "False").strip().lower() == "true"

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    # This fallback exists only so a local checkout can start without Render.
    # Production MUST define SECRET_KEY as an environment variable.
    if DEBUG:
        SECRET_KEY = "django-insecure-local-development-only"
    else:
        raise RuntimeError(
            "SECRET_KEY environment variable is required in production."
        )


RENDER_EXTERNAL_HOSTNAME = os.getenv(
    "RENDER_EXTERNAL_HOSTNAME",
    "",
).strip()


ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "investmetrics.co.tz",
    "www.investmetrics.co.tz",
]

if (
    RENDER_EXTERNAL_HOSTNAME
    and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS
):
    ALLOWED_HOSTS.append(
        RENDER_EXTERNAL_HOSTNAME
    )


# Optional comma-separated extra hosts for preview/test services.
for host in os.getenv(
    "ALLOWED_HOSTS",
    "",
).split(","):

    host = host.strip()

    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(
            host
        )


CSRF_TRUSTED_ORIGINS = [
    "https://investmetrics.co.tz",
    "https://www.investmetrics.co.tz",
]

if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(
        f"https://{RENDER_EXTERNAL_HOSTNAME}"
    )


for origin in os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "",
).split(","):

    origin = origin.strip()

    if (
        origin
        and origin not in CSRF_TRUSTED_ORIGINS
    ):
        CSRF_TRUSTED_ORIGINS.append(
            origin
        )


# Render terminates TLS at its proxy.
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


# -----------------------------------------------------------------------------
# Applications
# -----------------------------------------------------------------------------

INSTALLED_APPS = [

    # Unfold must be before django.contrib.admin.
    "unfold",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Existing Investmetrics website
    "app",

    # Investmetrics Learning
    "ai_at_work",

    # Existing third-party packages
    "rest_framework",
    "ckeditor",
    "widget_tweaks",
    "crispy_forms",
    "crispy_bootstrap4",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "investmetrics.urls"


TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django.DjangoTemplates"
        ),
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors."
                    "debug"
                ),
                (
                    "django.template.context_processors."
                    "request"
                ),
                (
                    "django.contrib.auth.context_processors."
                    "auth"
                ),
                (
                    "django.contrib.messages.context_processors."
                    "messages"
                ),
            ],
        },
    },
]


WSGI_APPLICATION = "investmetrics.wsgi.application"


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
# SQLite remains the fallback so the existing site can be tested immediately.
# Set DATABASE_URL to a Render PostgreSQL URL for durable production learner data.

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "",
).strip()


if DATABASE_URL:

    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=False,
        )
    }

else:

    DATABASES = {
        "default": {
            "ENGINE": (
                "django.db.backends.sqlite3"
            ),
            "NAME": (
                BASE_DIR / "db.sqlite3"
            ),
        }
    }


# -----------------------------------------------------------------------------
# Password validation
# -----------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]


# -----------------------------------------------------------------------------
# Internationalisation
# -----------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = os.getenv(
    "TIME_ZONE",
    "Africa/Dar_es_Salaam",
)

USE_I18N = True
USE_TZ = True


# -----------------------------------------------------------------------------
# Static / media
# -----------------------------------------------------------------------------

STATIC_URL = "/static/"

STATIC_ROOT = (
    BASE_DIR / "staticfiles"
)

STATICFILES_DIRS = [
    BASE_DIR / "app" / "static"
]


# Non-manifest WhiteNoise storage is deliberately used for the legacy site.
# It avoids a full-site 500 when an old template references an optional asset.

STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage."
            "FileSystemStorage"
        )
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedStaticFilesStorage"
        )
    },
}


# ============================================================
# Uploaded / private media storage
# ============================================================
#
# Local development:
#     MEDIA_ROOT defaults to BASE_DIR / "apps"
#
# Production on Render:
#     Set MEDIA_ROOT=/var/data after attaching a persistent disk
#     mounted at /var/data.
#
# Keeping the path environment-driven allows local development
# and production persistent storage to use the same codebase.

MEDIA_URL = "/apps/"

MEDIA_ROOT = Path(
    os.getenv(
        "MEDIA_ROOT",
        str(BASE_DIR / "apps"),
    )
)

MEDIA_TYPES = {
    "pdf": "application/pdf",
}


DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)


# -----------------------------------------------------------------------------
# Forms / editor
# -----------------------------------------------------------------------------

CRISPY_ALLOWED_TEMPLATE_PACKS = (
    "bootstrap4"
)

CRISPY_TEMPLATE_PACK = (
    "bootstrap4"
)


CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "full",
        "height": 300,
        "width": "100%",
        "removePlugins": "",
        "extraPlugins": ",".join(
            [
                "uploadimage",
                "div",
                "autolink",
                "autoembed",
                "embedsemantic",
                "autogrow",
                "widget",
                "lineutils",
                "clipboard",
                "dialog",
                "dialogui",
                "elementspath",
            ]
        ),
    },
}


# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------
#
# Email settings are controlled through environment variables.
#
# Local development may use the console backend if SMTP is not configured.
# Production should use the SMTP backend with the Investmetrics domain mailbox.
#
# IJIRI mailbox configuration:
#   SMTP host: mail.investmetrics.co.tz
#   SMTP port: 465
#   Security: SSL/TLS
#   Username: ijiri@investmetrics.co.tz
#
# Never hard-code the mailbox password in this file.

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    "mail.investmetrics.co.tz",
)

EMAIL_PORT = int(
    os.getenv(
        "EMAIL_PORT",
        "465",
    )
)

EMAIL_USE_TLS = (
    os.getenv(
        "EMAIL_USE_TLS",
        "False",
    )
    .strip()
    .lower()
    == "true"
)

EMAIL_USE_SSL = (
    os.getenv(
        "EMAIL_USE_SSL",
        "True",
    )
    .strip()
    .lower()
    == "true"
)

EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    "",
)

EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD",
    "",
)

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "ijiri@investmetrics.co.tz",
)

ADMIN_EMAIL = os.getenv(
    "ADMIN_EMAIL",
    "info@investmetrics.co.tz",
)

IJIRI_EDITORIAL_EMAIL = os.getenv(
    "IJIRI_EDITORIAL_EMAIL",
    "ijiri@investmetrics.co.tz",
)

# -----------------------------------------------------------------------------
# Investmetrics Learning email
# -----------------------------------------------------------------------------

LEARNING_EMAIL_HOST = os.getenv(
    "LEARNING_EMAIL_HOST",
    "mail.investmetrics.co.tz",
)

LEARNING_EMAIL_PORT = int(
    os.getenv(
        "LEARNING_EMAIL_PORT",
        "465",
    )
)

LEARNING_EMAIL_USE_TLS = (
    os.getenv(
        "LEARNING_EMAIL_USE_TLS",
        "False",
    ).lower()
    == "true"
)

LEARNING_EMAIL_USE_SSL = (
    os.getenv(
        "LEARNING_EMAIL_USE_SSL",
        "True",
    ).lower()
    == "true"
)

LEARNING_EMAIL_HOST_USER = os.getenv(
    "LEARNING_EMAIL_HOST_USER",
    "learn@investmetrics.co.tz",
)

LEARNING_EMAIL_HOST_PASSWORD = os.getenv(
    "LEARNING_EMAIL_HOST_PASSWORD",
    "",
)

LEARNING_FROM_EMAIL = os.getenv(
    "LEARNING_FROM_EMAIL",
    "learn@investmetrics.co.tz",
)

# -----------------------------------------------------------------------------
# Unfold admin
# -----------------------------------------------------------------------------

UNFOLD = {
    "SITE_HEADER": "Investmetrics",
}


# ============================================================
# PRODUCTION SECURITY
# ============================================================

# Render terminates HTTPS at its reverse proxy and forwards
# the original protocol through X-Forwarded-Proto.

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)


# Enable production-only HTTPS security controls.

if not DEBUG:

    SECURE_SSL_REDIRECT = True

    # Render performs its internal health check over HTTP.
    # Exempt only the dedicated health-check endpoint from HTTPS redirect.
    SECURE_REDIRECT_EXEMPT = [
        r"^healthz/?$"
    ]

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Start with a conservative HSTS period.
    # This can be increased after the production site is verified.
    SECURE_HSTS_SECONDS = int(
        os.getenv(
            "SECURE_HSTS_SECONDS",
            "3600",
        )
    )

    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

else:

    SECURE_SSL_REDIRECT = False
    SECURE_REDIRECT_EXEMPT = []

    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

    SECURE_HSTS_SECONDS = 0

    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"