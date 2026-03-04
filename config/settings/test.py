"""
Test settings for timecomply project.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# Use in-memory SQLite for fast tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
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
    m for m in MIDDLEWARE  # noqa: F405
    if m != "whitenoise.middleware.WhiteNoiseMiddleware"
]
