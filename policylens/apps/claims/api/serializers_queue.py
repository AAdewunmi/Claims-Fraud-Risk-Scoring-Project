# path: policylens/apps/claims/api/serializers_queue.py
"""
Queue serializers.

This contract is used by ops workflow surfaces later.
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from apps.claims.models import Claim


class QueueClaimSerializer(serializers.ModelSerializer):
    """Queue contract with SLA-derived fields."""

    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)
    sla_due_at = serializers.DateTimeField(source="sla_clock.due_at", read_only=True)
    sla_breached_at = serializers.DateTimeField(source="sla_clock.breached_at", read_only=True)
    sla_is_breached = serializers.SerializerMethodField()
    sla_seconds_remaining = serializers.SerializerMethodField()
    queue_rank = serializers.IntegerField(read_only=True)

    class Meta:
        model = Claim
        fields = [
            "queue_rank",
            "id",
            "policy_number",
            "claim_type",
            "status",
            "priority",
            "summary",
            "created_at",
            "sla_due_at",
            "sla_breached_at",
            "sla_is_breached",
            "sla_seconds_remaining",
        ]
        read_only_fields = fields

    def get_sla_is_breached(self, obj: Claim) -> bool:
        """Return True if the SLA due time has passed and claim is not decided."""
        due_at = getattr(getattr(obj, "sla_clock", None), "due_at", None)
        if not due_at:
            return False
        return due_at < timezone.now()

    def get_sla_seconds_remaining(self, obj: Claim) -> int | None:
        """Return seconds remaining until due_at, or 0 if already breached."""
        due_at = getattr(getattr(obj, "sla_clock", None), "due_at", None)
        if not due_at:
            return None
        delta = due_at - timezone.now()
        seconds = int(delta.total_seconds())
        return seconds if seconds > 0 else 0
