# path: policylens/tests/test_sla_breach_sweep.py
"""
Integration tests for SLA breach sweep evidence.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from policylens.apps.claims.models import AuditEvent, Claim, SlaClock
from tests.factories import PolicyFactory


@pytest.mark.django_db
def test_sla_breach_sweep_marks_breached_and_appends_audit_event():
    """Sweep should set breached_at and append SLA_BREACHED evidence."""
    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="Breach sweep",
        created_by="seed",
        status=Claim.Status.IN_REVIEW,
    )
    SlaClock.objects.create(
        claim=claim,
        started_at=claim.created_at,
        due_at=timezone.now() - timedelta(hours=1),
    )

    call_command("sweep_sla_breaches")

    clock = claim.sla_clock
    assert clock.breached_at is not None
    assert AuditEvent.objects.filter(claim=claim, event_type="SLA_BREACHED").exists()
