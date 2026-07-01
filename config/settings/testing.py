"""Testing settings."""

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = "test-secret-key-not-for-production"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="cast_it_test"),  # noqa: F405
        "USER": env("POSTGRES_USER", default="cast_it"),  # noqa: F405
        "PASSWORD": env("POSTGRES_PASSWORD", default="cast_it"),  # noqa: F405
        "HOST": env("POSTGRES_HOST", default="localhost"),  # noqa: F405
        "PORT": env("POSTGRES_PORT", default="5432"),  # noqa: F405
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

RAG_ENABLED = False

OLLAMA_CHAT_MODEL = "test-chat-model"
OLLAMA_EMBED_MODEL = "test-embed-model"
LLM_PROVIDER = "ollama"
OLLAMA_BASE_URL = "http://localhost:11434"
LLM_RETRY_COUNT = 3
LLM_MAX_PROMPT_CHARS = 100_000
