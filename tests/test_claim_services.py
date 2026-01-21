# path: policylens/tests/test_claim_services.py
"""
Unit tests for domain services.

These tests assert behaviour that must remain stable across API and UI layers.
"""

from __future__ import annotations

import pytest

from apps.claims import services
from apps.claims.models import AuditEvent, Claim
from tests.factories import PolicyFactory


@pytest.mark.django_db
def test_create_claim_appends_audit_event():
    """Creating a claim should also create a CLAIM_CREATED audit event."""
    policy = PolicyFactory(policy_number="PL-0001")

    claim = services.create_claim(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="Water damage in kitchen.",
        actor="reviewer-1",
    )

    assert claim.pk is not None
    assert claim.status == Claim.Status.NEW
    assert claim.created_by == "reviewer-1"

    event = AuditEvent.objects.filter(claim=claim,
                                      event_type="CLAIM_CREATED").first()
    assert event is not None
    assert event.actor == "reviewer-1"
    assert event.payload["policy_number"] == "PL-0001"
    assert event.payload["claim_type"] == Claim.Type.CLAIM
    assert event.payload["priority"] == Claim.Priority.NORMAL
