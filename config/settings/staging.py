"""Staging settings — production-like with safer defaults."""

from .production import *  # noqa: F403

DEBUG = env.bool("DJANGO_DEBUG", default=False)  # noqa: F405

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)  # noqa: F405
SECURE_HSTS_SECONDS = 0
