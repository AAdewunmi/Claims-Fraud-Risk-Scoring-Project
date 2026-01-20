# path: policylens/apps/claims/services.py
"""
Domain services for claims.

This module centralises business behaviour so
that API and UI share the same logic.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.claims.models import AuditEvent, Claim, Policy


def append_audit_event(
    *,
    claim: Claim,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
) -> AuditEvent:
    """Append an audit event for a claim.

    Args:
        claim: Claim the event relates to.
        event_type: Stable event type string.
        actor: Actor identifier (user id, email, or "system").
        payload: JSON-serialisable event details.

    Returns:
        The created AuditEvent.
    """
    return AuditEvent.objects.create(
        claim=claim,
        event_type=event_type,
        actor=actor,
        payload=payload,
    )


@transaction.atomic
def create_claim(
    *,
    policy: Policy,
    claim_type: str,
    priority: str,
    summary: str,
    actor: str,
) -> Claim:
    """Create a claim and append an initial audit event.

    Week 1 keeps rules minimal.
    Week 2 introduces roles and workflow transitions.

    Args:
        policy: Policy the claim is linked to.
        claim_type: Claim type value from Claim.Type choices.
        priority: Priority value from Claim.Priority choices.
        summary: Free text summary.
        actor: Actor identifier.

    Returns:
        The created Claim.
    """
    claim = Claim.objects.create(
        policy=policy,
        claim_type=claim_type,
        priority=priority,
        summary=summary,
        created_by=actor,
    )

    append_audit_event(
        claim=claim,
        event_type="CLAIM_CREATED",
        actor=actor,
        payload={
            "policy_number": policy.policy_number,
            "claim_type": claim_type,
            "priority": priority,
        },
    )

    return claim
