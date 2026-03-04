"""
Test settings for timecomply project.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# Use DATABASE_URL if set (CI/GitHub Actions with Postgres service),
# otherwise fall back to in-memory SQLite for fast local tests.
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///:memory:"),  # noqa: F405
}

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Use simple static files storage for tests (no manifest)
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable whitenoise in tests
MIDDLEWARE = [
    m
    for m in MIDDLEWARE  # noqa: F405
    if m != "whitenoise.middleware.WhiteNoiseMiddleware"
]
