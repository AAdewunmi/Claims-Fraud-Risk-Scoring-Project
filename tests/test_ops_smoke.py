# path: policylens/tests/test_ops_smoke.py
"""
Ops UI smoke tests.
"""

from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from tests.factories import ClaimFactory

User = get_user_model()


@pytest.mark.django_db
def test_ops_home_redirects_to_queue_for_logged_in_user(client):
    """Ops landing should redirect authenticated users to queue."""
    user = User.objects.create_user(username="ops_home_user", password="password123")
    client.force_login(user)

    url = reverse("ops:home")
    resp = client.get(url)
    assert resp.status_code == 302
    assert resp.url == reverse("ops:queue")


@pytest.mark.django_db
def test_ops_queue_page_renders_for_logged_in_user(client):
    """Queue page should be accessible and render expected content."""
    user = User.objects.create_user(username="ops_user", password="password123")
    client.force_login(user)

    url = reverse("ops:queue")
    resp = client.get(url)
    assert resp.status_code == 200
    assert any(t.name == "ops/queue.html" for t in resp.templates)
    assert "Review queue" in resp.content.decode("utf-8")


@pytest.mark.django_db
@patch("policylens.apps.ops.views.build_queue_queryset")
def test_ops_queue_applies_filters_and_assigns_queue_rank(mock_build_queue_queryset, client):
    """Queue view should pass filters into builder and assign one-based queue rank."""
    user = User.objects.create_user(username="ops_filter_user", password="password123")
    client.force_login(user)

    first = ClaimFactory()
    second = ClaimFactory()
    mock_build_queue_queryset.return_value = [first, second]

    url = reverse("ops:queue")
    resp = client.get(url, data={"status": "NEW", "priority": "HIGH", "sla": "breached"})

    assert resp.status_code == 200
    mock_build_queue_queryset.assert_called_once_with(
        status="NEW",
        priority="HIGH",
        sla_filter="breached",
    )
    assert resp.context["filters"] == {"status": "NEW", "priority": "HIGH", "sla": "breached"}
    assert resp.context["items"][0].queue_rank == 1
    assert resp.context["items"][1].queue_rank == 2


@pytest.mark.django_db
def test_ops_claim_detail_page_renders_for_logged_in_user(client):
    """Claim detail page should be accessible and render expected content."""
    user = User.objects.create_user(username="ops_detail_user", password="password123")
    client.force_login(user)
    claim = ClaimFactory()

    url = reverse("ops:claim-detail", kwargs={"claim_id": claim.pk})
    resp = client.get(url)

    assert resp.status_code == 200
    assert any(t.name == "ops/claim_detail.html" for t in resp.templates)
    assert resp.context["claim"].pk == claim.pk


@override_settings(DEBUG=True)
def test_root_urlpatterns_include_media_static_when_debug_true():
    """Root URLConf should append media static patterns in DEBUG."""
    urls_module = importlib.import_module("policylens.config.urls")
    reloaded = importlib.reload(urls_module)
    media_prefix = settings.MEDIA_URL.lstrip("/")
    assert any(
        str(pattern.pattern).startswith(f"^{media_prefix}") for pattern in reloaded.urlpatterns
    )
