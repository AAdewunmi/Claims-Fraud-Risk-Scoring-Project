# path: policylens/tests/test_ops_queue.py
"""
UI tests for ops queue.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from policylens.apps.claims.models import Claim, SlaClock
from tests.factories import PolicyFactory

User = get_user_model()


def _login_reviewer(client, *, username: str) -> None:
    """Create and log in a reviewer user for queue access tests."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    user = User.objects.create_user(username=username, password="password123")
    user.groups.add(reviewer_group)
    client.force_login(user)


@pytest.mark.django_db
def test_ops_queue_empty_state(client):
    """Queue should render empty state when no open claims exist."""
    _login_reviewer(client, username="ops_user2")

    url = reverse("ops:queue")
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["pagination"].paginator.count == 0
    assert list(resp.context["items"]) == []


@pytest.mark.django_db
def test_ops_queue_filter_priority(client):
    """Priority filter should reduce results."""
    _login_reviewer(client, username="ops_user3")

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

    SlaClock.objects.create(
        claim=c1, started_at=c1.created_at, due_at=timezone.now() + timedelta(days=1)
    )
    SlaClock.objects.create(
        claim=c2, started_at=c2.created_at, due_at=timezone.now() + timedelta(days=1)
    )

    url = reverse("ops:queue")
    resp = client.get(url, data={"priority": "HIGH"})
    assert resp.status_code == 200
    items = list(resp.context["items"])
    assert [c.id for c in items] == [c1.id]
    assert all(c.id != c2.id for c in items)
