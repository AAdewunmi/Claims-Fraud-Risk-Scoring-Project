# path: policylens/tests/test_queue_api.py
"""
Integration tests for queue API ordering and filters.
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
def test_queue_orders_breached_then_due_soon_then_priority_then_age(api_client):
    """Queue ordering should be deterministic and operationally meaningful."""
    user = User.objects.create_user(username="queue_user", password="password123")
    api_client.force_authenticate(user=user)

    policy = PolicyFactory()

    # Old low priority but breached
    breached_claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.LOW,
        summary="Breached",
        created_by="seed",
        status=Claim.Status.NEW,
    )
    SlaClock.objects.create(
        claim=breached_claim,
        started_at=breached_claim.created_at,
        due_at=timezone.now() - timedelta(hours=1),
    )

    # Due soon high priority
    due_soon_claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.HIGH,
        summary="Due soon",
        created_by="seed",
        status=Claim.Status.NEW,
    )
    SlaClock.objects.create(
        claim=due_soon_claim,
        started_at=due_soon_claim.created_at,
        due_at=timezone.now() + timedelta(hours=2),
    )

    # Not due soon, high priority, older
    normal_old_high = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.HIGH,
        summary="Normal older high",
        created_by="seed",
        status=Claim.Status.NEW,
    )
    SlaClock.objects.create(
        claim=normal_old_high,
        started_at=normal_old_high.created_at,
        due_at=timezone.now() + timedelta(days=2),
    )

    # Not due soon, normal priority, oldest
    normal_old_normal = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="Normal older normal",
        created_by="seed",
        status=Claim.Status.NEW,
    )
    SlaClock.objects.create(
        claim=normal_old_normal,
        started_at=normal_old_normal.created_at,
        due_at=timezone.now() + timedelta(days=2),
    )

    url = reverse("queue-claims")
    resp = api_client.get(url)
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()]

    assert ids[0] == breached_claim.id
    assert ids[1] == due_soon_claim.id
    assert ids.index(normal_old_high.id) < ids.index(normal_old_normal.id)


@pytest.mark.django_db
def test_queue_filter_sla_breached(api_client):
    """sla=breached filter should return only breached items."""
    user = User.objects.create_user(username="queue_user2", password="password123")
    api_client.force_authenticate(user=user)

    policy = PolicyFactory()
    c1 = Claim.objects.create(policy=policy, claim_type=Claim.Type.CLAIM, priority=Claim.Priority.NORMAL, summary="B", created_by="x")
    SlaClock.objects.create(claim=c1, started_at=c1.created_at, due_at=timezone.now() - timedelta(hours=1))

    c2 = Claim.objects.create(policy=policy, claim_type=Claim.Type.CLAIM, priority=Claim.Priority.NORMAL, summary="OK", created_by="x")
    SlaClock.objects.create(claim=c2, started_at=c2.created_at, due_at=timezone.now() + timedelta(days=1))

    url = reverse("queue-claims")
    resp = api_client.get(url, data={"sla": "breached"})
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert ids == {c1.id}
