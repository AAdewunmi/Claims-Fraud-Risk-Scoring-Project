# path: tests/test_healthcheck.py
"""
Integration tests for project-level health endpoints.

This file previously asserted a minimal {"status": "ok"} response.
It now asserts the readiness contract, keeping the same URL name.
"""

from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_healthcheck_returns_ok(api_client):
    """
    GET /api/health/ returns a readiness payload when the system is ready.
    """
    url = reverse("healthcheck")
    resp = api_client.get(url)

    assert resp.status_code == 200
    body = resp.json()

    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "ok"
