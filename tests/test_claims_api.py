# path: policylens/tests/test_claims_api.py
"""
Integration tests for the canonical claim API contract.

These tests hit the database and
validate the contract shape and persistence effects.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from policylens.apps.claims.models import AuditEvent, Claim
from tests.factories import ClaimFactory, PolicyFactory


@pytest.mark.django_db
def test_post_claim_creates_claim_and_audit_event(api_client):
    """POST /api/claims/ persists a claim and
    appends a CLAIM_CREATED audit event."""
    policy = PolicyFactory(policy_number="PL-7777")
    url = reverse("claims-list-create")

    payload = {
        "policy_id": policy.pk,
        "claim_type": Claim.Type.CLAIM,
        "priority": Claim.Priority.HIGH,
        "summary": "Broken window after storm.",
    }

    resp = api_client.post(url, data=payload, format="json")
    assert resp.status_code == 201, resp.content

    body = resp.json()
    assert body["policy_number"] == "PL-7777"
    assert body["status"] == Claim.Status.NEW
    assert body["priority"] == Claim.Priority.HIGH

    claim_id = body["id"]
    assert Claim.objects.filter(pk=claim_id).exists()
    assert AuditEvent.objects.filter(
        claim_id=claim_id, event_type="CLAIM_CREATED"
    ).exists()


@pytest.mark.django_db
def test_post_claim_sets_created_by_and_audit_actor_from_authenticated_user(
    api_client,
):
    """Authenticated POST /api/claims/ uses username,
    as actor and persists evidence."""
    User = get_user_model()
    user = User.objects.create_user(username="reviewer-1",
                                    password="password123")

    api_client.force_authenticate(user=user)

    policy = PolicyFactory(policy_number="PL-8888")
    url = reverse("claims-list-create")

    payload = {
        "policy_id": policy.pk,
        "claim_type": Claim.Type.CLAIM,
        "priority": Claim.Priority.NORMAL,
        "summary": "Water damage in kitchen.",
    }

    resp = api_client.post(url, data=payload, format="json")
    assert resp.status_code == 201, resp.content

    body = resp.json()
    claim_id = body["id"]

    assert body["created_by"] == "reviewer-1"
    assert Claim.objects.filter(pk=claim_id, created_by="reviewer-1").exists()

    event = AuditEvent.objects.filter(
        claim_id=claim_id, event_type="CLAIM_CREATED"
    ).first()
    assert event is not None
    assert event.actor == "reviewer-1"


@pytest.mark.django_db
def test_get_claims_filters_by_status_and_priority(api_client):
    """GET /api/claims/?status=&priority= filters deterministically."""
    ClaimFactory(status=Claim.Status.NEW, priority=Claim.Priority.NORMAL)
    ClaimFactory(status=Claim.Status.IN_REVIEW, priority=Claim.Priority.HIGH)
    ClaimFactory(status=Claim.Status.IN_REVIEW, priority=Claim.Priority.NORMAL)

    url = reverse("claims-list-create")

    resp = api_client.get(
        url,
        data={
            "status": Claim.Status.IN_REVIEW,
            "priority": Claim.Priority.NORMAL,
        },
    )
    assert resp.status_code == 200

    results = resp.json()
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["status"] == Claim.Status.IN_REVIEW
    assert results[0]["priority"] == Claim.Priority.NORMAL
