# path: policylens/tests/test_claims_api.py
"""
Integration tests for the canonical claim API contract.

These tests hit the database and
validate the contract shape and persistence effects.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.claims.models import AuditEvent, Claim
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
    assert AuditEvent.objects.filter(claim_id=claim_id, event_type="CLAIM_CREATED").exists()