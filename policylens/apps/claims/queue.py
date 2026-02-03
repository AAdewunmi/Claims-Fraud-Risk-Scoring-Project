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


def build_queue_queryset(*, now=None, status: str | None, priority: str | None, sla_filter: str | None):
    """Build a queryset for the ops review queue.

    Args:
        now: Optional override for deterministic testing.
        status: Optional claim status filter.
        priority: Optional priority filter.
        sla_filter: Optional SLA filter: breached, due_soon, ok.

    Returns:
        Queryset ordered by operational priority.
    """
    now = now or timezone.now()
    due_soon_cutoff = now + DUE_SOON_WINDOW

    qs = (
        Claim.objects.select_related("policy", "sla_clock")
        .filter(status__in=[Claim.Status.NEW, Claim.Status.IN_REVIEW])
        .annotate(
            priority_weight=_priority_weight_case(),
            is_breached=Case(
                When(
                    Q(sla_clock__due_at__isnull=False) & Q(sla_clock__due_at__lt=now),
                    then=Value(1),
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
            is_due_soon=Case(
                When(
                    Q(sla_clock__due_at__isnull=False)
                    & Q(sla_clock__due_at__gte=now)
                    & Q(sla_clock__due_at__lte=due_soon_cutoff),
                    then=Value(1),
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
    )

    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)

    if sla_filter == "breached":
        qs = qs.filter(is_breached=1)
    elif sla_filter == "due_soon":
        qs = qs.filter(is_breached=0, is_due_soon=1)
    elif sla_filter == "ok":
        qs = qs.filter(is_breached=0, is_due_soon=0)

    return qs.order_by("-is_breached", "-is_due_soon", "-priority_weight", "created_at")
