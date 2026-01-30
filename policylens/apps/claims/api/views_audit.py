# path: policylens/apps/claims/api/views_audit.py
"""Audit event API views."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.claims.api.serializers_audit import AuditEventSerializer
from apps.claims.models import AuditEvent, Claim


class ClaimAuditEventListAPIView(ListAPIView):
    """List audit events for a claim in reverse chronological order.

    Contract:
    - GET /api/claims/{id}/audit-events/
    """

    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return audit events for a claim."""
        claim = get_object_or_404(Claim, pk=self.kwargs["claim_id"])
        return AuditEvent.objects.filter(claim=claim).order_by("-created_at")
