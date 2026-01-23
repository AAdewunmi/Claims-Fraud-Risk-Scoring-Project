# path: tests/test_healthcheck.py
"""
Integration tests for project-level health endpoints.

These tests validate that routing and JSON responses behave correctly in a
containerised runtime and in CI.
"""

from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_healthcheck_returns_ok(api_client):
    """GET /api/health/ returns a minimal status payload."""
    url = reverse("healthcheck")

    resp = api_client.get(url)
    assert resp.status_code == 200

    body = resp.json()
    assert body == {"status": "ok"}
