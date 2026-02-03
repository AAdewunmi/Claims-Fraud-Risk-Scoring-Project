# path: policylens/apps/claims/queue.py
"""
Queue building logic for ops review.

Ordering rules (Week 3):
1. SLA breached first
2. SLA due soon (within N hours) next
3. Higher priority first
4. Older claims first (created_at ascending)

Filters:
- status (optional)
- priority (optional)
- sla: breached | due_soon | ok (optional)
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

from apps.claims.models import Claim


DUE_SOON_WINDOW = timedelta(hours=6)

PRIORITY_WEIGHT = {
    Claim.Priority.HIGH: 3,
    Claim.Priority.NORMAL: 2,
    Claim.Priority.LOW: 1,
}


def _priority_weight_case() -> Case:
    """Return a DB CASE expression for priority weighting."""
    return Case(
        When(priority=Claim.Priority.HIGH, then=Value(PRIORITY_WEIGHT[Claim.Priority.HIGH])),
        When(priority=Claim.Priority.NORMAL, then=Value(PRIORITY_WEIGHT[Claim.Priority.NORMAL])),
        When(priority=Claim.Priority.LOW, then=Value(PRIORITY_WEIGHT[Claim.Priority.LOW])),
        default=Value(PRIORITY_WEIGHT[Claim.Priority.NORMAL]),
        output_field=IntegerField(),
    )