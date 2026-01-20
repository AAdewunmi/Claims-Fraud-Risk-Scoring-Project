# path: policylens/apps/claims/api/views.py
"""API views for claims."""

from __future__ import annotations

from rest_framework.generics import ListCreateAPIView

from policylens.apps.claims.api.serializers import ClaimSerializer
from policylens.apps.claims.models import Claim


class ClaimListCreateAPIView(ListCreateAPIView):
    """List and create claims.

    Contract:
    - GET /api/claims/?status=&priority=
    - POST /api/claims/
    """

    serializer_class = ClaimSerializer

    def get_queryset(self):
        """Return queryset filtered by the canonical query parameters."""
        qs = Claim.objects.select_related("policy").all()
        status = self.request.query_params.get("status")
        priority = self.request.query_params.get("priority")

        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)

        return qs.order_by("-created_at")

    def get_serializer_context(self):
        """Pass actor context into serializers for service-layer writes."""
        ctx = super().get_serializer_context()
        user = getattr(self.request, "user", None)
        actor = "anonymous"
        if user and getattr(user, "is_authenticated", False):
            actor = user.get_username() or str(user.pk)
        ctx["actor"] = actor
        return ctx
