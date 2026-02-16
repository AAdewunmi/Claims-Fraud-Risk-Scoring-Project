# path: policylens/tests/test_ops_smoke.py
"""
Ops UI smoke tests.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_ops_queue_page_renders_for_logged_in_user(client):
    """Queue page should be accessible and render expected content."""
    user = User.objects.create_user(username="ops_user", password="password123")
    client.force_login(user)

    url = reverse("ops:queue")
    resp = client.get(url)
    assert resp.status_code == 200
    assert "Review queue" in resp.content.decode("utf-8")
