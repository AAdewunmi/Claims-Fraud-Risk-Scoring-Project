"""
Ops queue behavioural tests.

Week 6 update
- Ops queue is reviewer-surface behaviour.
- Tests must authenticate as a user in the reviewer group (or admin).
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

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture()
def reviewer_user():
    """Create a reviewer-group user for queue access tests."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    user = User.objects.create_user(username="reviewer_ops", password="pass-12345-strong")
    user.groups.add(reviewer_group)
    return user


def test_ops_queue_requires_reviewer_role(client, reviewer_user):
    client.force_login(reviewer_user)
    response = client.get("/ops/queue/")
    assert response.status_code == 200
    assert b"Reviewer queue" in response.content


def test_ops_queue_empty_state(client, reviewer_user):
    """Queue should render empty state when no open claims exist."""
    client.force_login(reviewer_user)

    url = reverse("ops:queue")
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["pagination"].paginator.count == 0
    assert list(resp.context["items"]) == []


def test_ops_queue_filter_priority(client, reviewer_user):
    """Priority filter should reduce results."""
    client.force_login(reviewer_user)

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
