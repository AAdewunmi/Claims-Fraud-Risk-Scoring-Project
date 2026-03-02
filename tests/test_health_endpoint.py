# path: tests/test_health_endpoint.py
"""
Integration tests for the readiness health endpoint.

These tests verify:
- success path returns 200 and a structured readiness payload
- failure path returns 503 and a structured readiness payload
- database checker returns a stable error code on OperationalError
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.db.utils import OperationalError
from django.urls import reverse

from policylens.apps.api.views_health import check_database


@pytest.mark.django_db
def test_readiness_health_returns_ok(api_client):
    """
    GET /api/health/ returns 200 when database connectivity is available.
    """
    url = reverse("healthcheck")
    resp = api_client.get(url)

    assert resp.status_code == 200
    body = resp.json()

    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"


@pytest.mark.django_db
def test_readiness_health_returns_503_on_database_failure(api_client):
    """
    GET /api/health/ returns 503 when the database check fails.
    """
    url = reverse("healthcheck")

    # Patch at the module boundary to keep the test deterministic and avoid
    # destabilising unrelated DB usage inside the test harness.
    with patch(
        "policylens.apps.api.views_health.check_database",
        return_value=(False, "OperationalError"),
    ):
        resp = api_client.get(url)

    assert resp.status_code == 503
    body = resp.json()

    assert body["status"] == "error"
    assert body["checks"]["database"]["status"] == "error"
    assert body["checks"]["database"]["error"] == "OperationalError"


@pytest.mark.django_db
def test_check_database_returns_operational_error_code_when_cursor_raises():
    """
    check_database returns (False, "OperationalError") when the DB cursor raises.
    """
    with patch(
        "django.db.backends.base.base.BaseDatabaseWrapper.cursor",
        side_effect=OperationalError,
    ):
        ok, err = check_database()

    assert ok is False
    assert err == "OperationalError"
