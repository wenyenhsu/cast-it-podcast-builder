"""Base Django settings shared across all environments."""

from pathlib import Path

import environ  # type: ignore[import-untyped]

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS: list[str] = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    # Local apps
    "apps.core",
    "apps.users",
    "apps.articles",
    "apps.episodes",
    "apps.scripts",
    "apps.audio",
    "apps.publish",
    "apps.scheduler",
    "apps.providers",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="cast_it"),
        "USER": env("POSTGRES_USER", default="cast_it"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="cast_it"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
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

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redis / Cache
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=3600)
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=3300)
CELERY_TASK_MAX_RETRIES = env.int("CELERY_TASK_MAX_RETRIES", default=3)
CELERY_DEFAULT_QUEUE = env("CELERY_DEFAULT_QUEUE", default="default")
CELERY_RETRY_BASE_DELAY = env.int("CELERY_RETRY_BASE_DELAY", default=60)
CELERY_RETRY_MAX_DELAY = env.int("CELERY_RETRY_MAX_DELAY", default=900)

# Beat cron schedules (minute hour day month day_of_week)
BEAT_IMPORT_NEWS_CRON = env("BEAT_IMPORT_NEWS_CRON", default="0 6 * * *")
BEAT_EPISODE_PLANNING_CRON = env("BEAT_EPISODE_PLANNING_CRON", default="0 7 * * *")
BEAT_GENERATE_SCRIPT_CRON = env("BEAT_GENERATE_SCRIPT_CRON", default="0 8 * * *")
BEAT_GENERATE_AUDIO_CRON = env("BEAT_GENERATE_AUDIO_CRON", default="0 9 * * *")
BEAT_PUBLISH_EPISODE_CRON = env("BEAT_PUBLISH_EPISODE_CRON", default="0 10 * * *")
BEAT_RETRY_SWEEP_CRON = env("BEAT_RETRY_SWEEP_CRON", default="*/30 * * * *")
BEAT_HEALTH_CHECK_CRON = env("BEAT_HEALTH_CHECK_CRON", default="*/15 * * * *")

from infrastructure.celery.beat_schedule import build_beat_schedule  # noqa: E402
from infrastructure.celery.routing import TASK_ROUTES  # noqa: E402

CELERY_BEAT_SCHEDULE = build_beat_schedule()
CELERY_TASK_ROUTES = TASK_ROUTES

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "api.v1.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "api.v1.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Cast It Podcast Generator API",
    "DESCRIPTION": (
        "REST API for the AI Podcast Generator platform. "
        "Long-running operations return 202 Accepted with a job reference."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# LLM
LLM_PROVIDER = env("LLM_PROVIDER", default="ollama")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", default="http://localhost:11434")
OLLAMA_CHAT_MODEL = env("OLLAMA_CHAT_MODEL", default="")
OLLAMA_EMBED_MODEL = env("OLLAMA_EMBED_MODEL", default="")
LLM_TEMPERATURE = env.float("LLM_TEMPERATURE", default=0.7)
LLM_TIMEOUT = env.float("LLM_TIMEOUT", default=60.0)
LLM_RETRY_COUNT = env.int("LLM_RETRY_COUNT", default=3)
LLM_MAX_PROMPT_CHARS = env.int("LLM_MAX_PROMPT_CHARS", default=100_000)

# TTS (Chatterbox)
TTS_PROVIDER = env("TTS_PROVIDER", default="chatterbox")
CHATTERBOX_BASE_URL = env("CHATTERBOX_BASE_URL", default="http://localhost:8004")
CHATTERBOX_TIMEOUT = env.float("CHATTERBOX_TIMEOUT", default=120.0)
CHATTERBOX_DEFAULT_VOICE = env("CHATTERBOX_DEFAULT_VOICE", default="")
CHATTERBOX_AUDIO_FORMAT = env("CHATTERBOX_AUDIO_FORMAT", default="wav")
TTS_MAX_TEXT_LENGTH = env.int("TTS_MAX_TEXT_LENGTH", default=5000)
TTS_WORDS_PER_MINUTE = env.int("TTS_WORDS_PER_MINUTE", default=150)
AUDIO_STORAGE_SUBDIR = env("AUDIO_STORAGE_SUBDIR", default="audio")

# Audio Pipeline (FFmpeg)
AUDIO_OUTPUT_SUBDIR = env("AUDIO_OUTPUT_SUBDIR", default="audio")
AUDIO_DEFAULT_BITRATE = env.int("AUDIO_DEFAULT_BITRATE", default=192)
AUDIO_DEFAULT_SAMPLE_RATE = env.int("AUDIO_DEFAULT_SAMPLE_RATE", default=44100)
AUDIO_DEFAULT_SILENCE_SECONDS = env.float("AUDIO_DEFAULT_SILENCE_SECONDS", default=0.75)
AUDIO_INTRO_FILE_PATH = env("AUDIO_INTRO_FILE_PATH", default="")
AUDIO_OUTRO_FILE_PATH = env("AUDIO_OUTRO_FILE_PATH", default="")
AUDIO_BACKGROUND_MUSIC_PATH = env("AUDIO_BACKGROUND_MUSIC_PATH", default="")
AUDIO_ENABLE_BACKGROUND_MUSIC = env.bool("AUDIO_ENABLE_BACKGROUND_MUSIC", default=False)
AUDIO_ENABLE_NORMALIZATION = env.bool("AUDIO_ENABLE_NORMALIZATION", default=True)
AUDIO_BACKGROUND_MUSIC_VOLUME = env.float("AUDIO_BACKGROUND_MUSIC_VOLUME", default=0.15)
AUDIO_TARGET_LUFS = env.float("AUDIO_TARGET_LUFS", default=-16.0)
FFMPEG_BINARY = env("FFMPEG_BINARY", default="ffmpeg")
FFPROBE_BINARY = env("FFPROBE_BINARY", default="ffprobe")
FFMPEG_TIMEOUT = env.float("FFMPEG_TIMEOUT", default=300.0)

# Publishing
YOUTUBE_API_KEY = env("YOUTUBE_API_KEY", default="")
YOUTUBE_CLIENT_ID = env("YOUTUBE_CLIENT_ID", default="")
YOUTUBE_CLIENT_SECRET = env("YOUTUBE_CLIENT_SECRET", default="")
YOUTUBE_CHANNEL_ID = env("YOUTUBE_CHANNEL_ID", default="")
ENABLE_YOUTUBE_PUBLISHING = env.bool("ENABLE_YOUTUBE_PUBLISHING", default=False)
ENABLE_RSS_PUBLISHING = env.bool("ENABLE_RSS_PUBLISHING", default=True)
RSS_FEED_TITLE = env("RSS_FEED_TITLE", default="Cast It Podcast")
RSS_FEED_SUBTITLE = env(
    "RSS_FEED_SUBTITLE",
    default="AI-generated podcast episodes",
)
RSS_FEED_AUTHOR = env("RSS_FEED_AUTHOR", default="Cast It")
RSS_FEED_LANGUAGE = env("RSS_FEED_LANGUAGE", default="en-us")
RSS_FEED_SITE_URL = env("RSS_FEED_SITE_URL", default="https://example.com")
RSS_FEED_AUDIO_BASE_URL = env(
    "RSS_FEED_AUDIO_BASE_URL",
    default="https://example.com/media",
)
RSS_FEED_OUTPUT_PATH = env("RSS_FEED_OUTPUT_PATH", default="feeds/podcast.xml")
