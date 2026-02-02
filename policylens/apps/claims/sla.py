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

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from apps.claims.models import Claim, SlaClock


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