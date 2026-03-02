# path: tests/test_healthcheck.py
"""
Integration tests for project-level health endpoints.

These tests validate that routing and JSON responses behave correctly in a
containerised runtime and in CI.
"""

from __future__ import annotations

import pytest
from django.db.utils import OperationalError
from django.urls import reverse

from policylens.apps.api import views_health


@pytest.mark.django_db
def test_healthcheck_returns_ok(api_client):
    """GET /api/health/ returns readiness status and database check details."""
    url = reverse("healthcheck")

    resp = api_client.get(url)
    assert resp.status_code == 200

    body = resp.json()
    assert body == {
        "status": "ok",
        "checks": {
            "database": {
                "status": "ok",
            }
        },
    }


def test_healthcheck_returns_503_when_database_not_ready(api_client, monkeypatch):
    """GET /api/health/ returns 503 and an error code when DB check fails."""
    monkeypatch.setattr(views_health, "check_database", lambda: (False, "OperationalError"))

    resp = api_client.get(reverse("healthcheck"))

    assert resp.status_code == 503
    assert resp.json() == {
        "status": "error",
        "checks": {
            "database": {
                "status": "error",
                "error": "OperationalError",
            }
        },
    }


def test_check_database_returns_unexpected_select_result(monkeypatch):
    """check_database should fail when SELECT does not return the expected row."""

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, _query):
            return None

        def fetchone(self):
            return None

    class _Connection:
        def cursor(self):
            return _Cursor()

    monkeypatch.setattr(views_health, "connections", {"default": _Connection()})

    assert views_health.check_database() == (False, "UnexpectedSelectResult")


def test_check_database_returns_operational_error_code(monkeypatch):
    """check_database should map OperationalError to a stable error code."""

    class _Connection:
        def cursor(self):
            raise OperationalError("db unavailable")

    monkeypatch.setattr(views_health, "connections", {"default": _Connection()})

    assert views_health.check_database() == (False, "OperationalError")


def test_check_database_returns_exception_class_name(monkeypatch):
    """check_database should map unexpected exceptions to class name strings."""

    class _Connection:
        def cursor(self):
            raise RuntimeError("unexpected")

    monkeypatch.setattr(views_health, "connections", {"default": _Connection()})

    assert views_health.check_database() == (False, "RuntimeError")
