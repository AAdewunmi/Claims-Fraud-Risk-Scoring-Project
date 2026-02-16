# path: policylens/tests/test_ops_smoke.py
"""
Ops UI smoke tests.
"""

from __future__ import annotations

import importlib

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

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


@override_settings(DEBUG=True)
def test_root_urlpatterns_include_media_static_when_debug_true():
    """Root URLConf should append media static patterns in DEBUG."""
    urls_module = importlib.import_module("policylens.config.urls")
    reloaded = importlib.reload(urls_module)
    media_prefix = settings.MEDIA_URL.lstrip("/")
    assert any(
        str(pattern.pattern).startswith(f"^{media_prefix}")
        for pattern in reloaded.urlpatterns
    )
