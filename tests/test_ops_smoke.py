# path: policylens/tests/test_ops_smoke.py
"""
Ops UI smoke tests.
"""

from __future__ import annotations

import importlib

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import override_settings
from django.urls import reverse

from policylens.apps.claims.models import Claim
from tests.factories import ClaimFactory, PolicyFactory

User = get_user_model()


def _login_reviewer(client, *, username: str) -> None:
    """Create and log in a reviewer user for queue access tests."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    user = User.objects.create_user(username=username, password="password123")
    user.groups.add(reviewer_group)
    client.force_login(user)


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
    _login_reviewer(client, username="ops_user")

    url = reverse("ops:queue")
    resp = client.get(url)
    assert resp.status_code == 200
    assert any(t.name == "ops/queue.html" for t in resp.templates)
    assert "pagination" in resp.context
    assert "items" in resp.context


@pytest.mark.django_db
def test_ops_queue_applies_filters_and_exposes_pagination_context(client):
    """Queue view should filter by supported params and expose pagination context."""
    _login_reviewer(client, username="ops_filter_user")
    policy = PolicyFactory()
    c1 = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.HIGH,
        summary="H",
        created_by="x",
        status=Claim.Status.NEW,
    )
    c2 = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.LOW,
        summary="L",
        created_by="x",
        status=Claim.Status.NEW,
    )

    url = reverse("ops:queue")
    resp = client.get(url, data={"status": "NEW", "priority": "HIGH", "sla": "breached"})

    assert resp.status_code == 200
    assert resp.context["filters"]["status"] == "NEW"
    assert resp.context["filters"]["priority"] == "HIGH"
    assert resp.context["filters"]["sla"] == "breached"
    assert "pagination" in resp.context
    items = list(resp.context["items"])
    assert items == list(resp.context["pagination"].page_obj.object_list)
    assert [item.id for item in items] == [c1.id]
    assert all(item.id != c2.id for item in items)


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
