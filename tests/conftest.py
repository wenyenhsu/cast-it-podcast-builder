"""Pytest configuration and shared fixtures."""

import pytest
from django.test import Client


@pytest.fixture
def api_client() -> Client:
    """Return a Django test client."""
    return Client()
