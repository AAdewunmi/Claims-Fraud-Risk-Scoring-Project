# path: policylens/tests/conftest.py
"""
Pytest configuration for PolicyLens.

Fixtures here are shared across unit and integration tests.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient


@pytest.fixture()
def api_client() -> APIClient:
    """Return a DRF APIClient instance."""
    return APIClient()
