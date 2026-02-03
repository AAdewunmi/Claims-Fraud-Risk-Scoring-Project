# path: policylens/apps/claims/api/views_queue.py
"""Queue API views."""

from __future__ import annotations

from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from policylens.apps.claims.api.serializers_queue import QueueClaimSerializer
from policylens.apps.claims.models import Claim
from policylens.apps.claims.queue import build_queue_queryset


VALID_SLA_FILTERS = {None, "breached", "due_soon", "ok"}


def _validate_choice(value: str | None, *, allowed: set[str], field: str) -> None:
    """Validate query parameter choice values."""
    if value is None:
        return
    if value not in allowed:
        raise ValidationError({field: f"Invalid value '{value}'."})


class QueueClaimListAPIView(ListAPIView):
    """List claims in operational priority order.

    Contract:
    - GET /api/queue/claims/?status=&priority=&sla=
    """

    serializer_class = QueueClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return prioritised queue queryset."""
        status = self.request.query_params.get("status") or None
        priority = self.request.query_params.get("priority") or None
        sla_filter = self.request.query_params.get("sla") or None

        _validate_choice(status, allowed={c[0] for c in Claim.Status.choices}, field="status")
        _validate_choice(priority, allowed={c[0] for c in Claim.Priority.choices}, field="priority")
        _validate_choice(sla_filter, allowed=VALID_SLA_FILTERS, field="sla")

        return build_queue_queryset(status=status, priority=priority, sla_filter=sla_filter)

    def list(self, request, *args, **kwargs):
        """Assign queue rank based on response ordering."""
        queryset = list(self.get_queryset())
        for idx, obj in enumerate(queryset, start=1):
            setattr(obj, "queue_rank", idx)

        serializer = self.get_serializer(queryset, many=True)
        from rest_framework.response import Response  # local import for clarity

        return Response(serializer.data)
