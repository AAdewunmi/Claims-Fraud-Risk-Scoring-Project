# path: policylens/apps/claims/sla.py
"""
SLA rules and utilities for PolicyLens.

SLA clocks are operational evidence. Rules must be deterministic and testable.

Week 3 scope:
- Compute due_at based on claim priority.
- Create SLA clocks when missing.
- Detect breaches.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from policylens.apps.claims.models import Claim, SlaClock


@dataclass(frozen=True)
class SlaPolicy:
    """SLA policy parameters.

    Args:
        due_window: Time delta from the anchor (claim creation) to due time.
        due_soon_window: Used later by queue prioritisation.
    """

    due_window: timedelta
    due_soon_window: timedelta


DEFAULT_DUE_SOON_WINDOW = timedelta(hours=6)

PRIORITY_TO_SLA_POLICY: dict[str, SlaPolicy] = {
    Claim.Priority.HIGH: SlaPolicy(due_window=timedelta(hours=24), due_soon_window=DEFAULT_DUE_SOON_WINDOW),
    Claim.Priority.NORMAL: SlaPolicy(due_window=timedelta(hours=72), due_soon_window=DEFAULT_DUE_SOON_WINDOW),
    Claim.Priority.LOW: SlaPolicy(due_window=timedelta(hours=120), due_soon_window=DEFAULT_DUE_SOON_WINDOW),
}


def compute_due_at(*, claim: Claim, anchor_time) -> timezone.datetime:
    """Compute SLA due time for a claim.

    Args:
        claim: Claim to compute due time for.
        anchor_time: Datetime used as the SLA start anchor, typically claim.created_at.

    Returns:
        Timezone-aware due_at datetime.
    """
    policy = PRIORITY_TO_SLA_POLICY.get(claim.priority) or PRIORITY_TO_SLA_POLICY[Claim.Priority.NORMAL]
    return anchor_time + policy.due_window


@transaction.atomic
def ensure_sla_clock_exists(*, claim: Claim) -> SlaClock:
    """Ensure the claim has an SLA clock with a deterministic due_at.

    Uses claim.created_at as the anchor to remain reproducible across environments.

    Args:
        claim: Claim to ensure SLA clock for.

    Returns:
        The existing or created SlaClock.
    """
    try:
        return claim.sla_clock
    except SlaClock.DoesNotExist:
        anchor = claim.created_at
        due_at = compute_due_at(claim=claim, anchor_time=anchor)
        clock = SlaClock.objects.create(
            claim=claim,
            started_at=anchor,
            due_at=due_at,
        )
        if clock.started_at != anchor or clock.due_at != due_at:
            SlaClock.objects.filter(pk=clock.pk).update(started_at=anchor, due_at=due_at)
            clock.refresh_from_db(fields=["started_at", "due_at"])
        return clock


def find_breached_clocks(*, now) -> Iterable[SlaClock]:
    """Return clocks that are currently breached and not yet marked.

    Args:
        now: Current time.

    Returns:
        Iterable of SlaClock objects.
    """
    return (
        SlaClock.objects.select_related("claim")
        .filter(breached_at__isnull=True, due_at__isnull=False, due_at__lt=now)
        .exclude(claim__status=Claim.Status.DECIDED)
        .order_by("due_at")
    )
