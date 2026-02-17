# path: policylens/tests/test_ops_queue.py
"""
UI tests for ops queue.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from policylens.apps.claims.models import Claim, SlaClock
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_ops_queue_empty_state(client):
    """Queue should render empty state when no open claims exist."""
    user = User.objects.create_user(username="ops_user2", password="password123")
    client.force_login(user)

    url = reverse("ops:queue")
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "No claims to review" in html


@pytest.mark.django_db
def test_ops_queue_filter_priority(client):
    """Priority filter should reduce results."""
    user = User.objects.create_user(username="ops_user3", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    c1 = Claim.objects.create(policy=policy, claim_type=Claim.Type.CLAIM, priority=Claim.Priority.HIGH, summary="H", created_by="x", status=Claim.Status.NEW)
    c2 = Claim.objects.create(policy=policy, claim_type=Claim.Type.CLAIM, priority=Claim.Priority.LOW, summary="L", created_by="x", status=Claim.Status.NEW)

    SlaClock.objects.create(claim=c1, started_at=c1.created_at, due_at=timezone.now() + timedelta(days=1))
    SlaClock.objects.create(claim=c2, started_at=c2.created_at, due_at=timezone.now() + timedelta(days=1))

    url = reverse("ops:queue")
    resp = client.get(url, data={"priority": "HIGH"})
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "#{}".format(c1.id) in html
    assert "#{}".format(c2.id) not in html
