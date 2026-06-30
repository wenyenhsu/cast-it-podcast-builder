"""Deployment settings smoke tests."""

import importlib


def test_production_settings_import() -> None:
    module = importlib.import_module("config.settings.production")
    assert hasattr(module, "SECURE_SSL_REDIRECT")
    assert hasattr(module, "USE_S3_STORAGE")


def test_staging_settings_import() -> None:
    module = importlib.import_module("config.settings.staging")
    assert hasattr(module, "SECURE_SSL_REDIRECT")


def test_testing_settings_import() -> None:
    module = importlib.import_module("config.settings.testing")
    assert module.CELERY_TASK_ALWAYS_EAGER is True
