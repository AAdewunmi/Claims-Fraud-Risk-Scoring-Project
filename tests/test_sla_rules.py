# path: policylens/tests/test_sla_rules.py
"""
Tests for SLA rules and SLA clock creation.

Sprint 3 validates determinism:
- due_at depends on claim.created_at and priority
- SLA clock is created when a claim is created
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from policylens.apps.claims import sla
from policylens.apps.claims.models import Claim
from policylens.apps.claims.services import create_claim
from tests.factories import PolicyFactory


@pytest.mark.django_db
def test_compute_due_at_high_priority_is_24_hours_from_anchor():
    """High priority due date should be 24 hours from the anchor time."""
    policy = PolicyFactory()
    claim = Claim(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.HIGH,
        summary="Test",
        created_by="tester",
    )
    anchor = timezone.now()
    due_at = sla.compute_due_at(claim=claim, anchor_time=anchor)
    assert due_at == anchor + timedelta(hours=24)


@pytest.mark.django_db
def test_create_claim_creates_sla_clock_with_due_at():
    """Creating a claim should also create an SLA clock with due_at set."""
    policy = PolicyFactory()
    claim = create_claim(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="SLA creation test.",
        actor="reviewer-1",
    )
    clock = claim.sla_clock
    assert clock.due_at is not None
    assert clock.started_at == claim.created_at
