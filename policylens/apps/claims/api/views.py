# path: policylens/apps/claims/api/views.py
"""API views for claims."""

from __future__ import annotations

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, MultiPartParser

from policylens.apps.claims import services
from policylens.apps.claims.api.serializers import (
    ClaimDetailSerializer,
    ClaimDocumentSerializer,
    ClaimDocumentUploadSerializer,
    ClaimSerializer,
    InternalNoteCreateSerializer,
    InternalNoteSerializer,
    ReviewDecisionCreateSerializer,
    ReviewDecisionSerializer,
)
from policylens.apps.claims.models import Claim, ClaimDocument, InternalNote, ReviewDecision


def _actor_from_request(request) -> str:
    """Return a stable actor id for audit events."""
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return user.get_username() or str(user.pk)
    return "anonymous"


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
        ctx["actor"] = _actor_from_request(self.request)
        return ctx


class ClaimRetrieveAPIView(RetrieveAPIView):
    """Retrieve claim detail.

    Contract:
    - GET /api/claims/{id}/
    """

    serializer_class = ClaimDetailSerializer
    lookup_url_kwarg = "claim_id"

    def get_queryset(self):
        """Annotate counts used by ops views."""
        return (
            Claim.objects.select_related("policy")
            .annotate(
                documents_count=Count("documents", distinct=True),
                notes_count=Count("notes", distinct=True),
                decisions_count=Count("decisions", distinct=True),
            )
            .all()
        )


class ClaimDocumentUploadAPIView(CreateAPIView):
    """Upload a document for a claim.

    Contract:
    - POST /api/claims/{id}/documents/
    """

    serializer_class = ClaimDocumentUploadSerializer
    parser_classes = [MultiPartParser, FormParser]
    lookup_url_kwarg = "claim_id"

    def get_serializer_context(self):
        """Provide claim and actor to serializer create method."""
        ctx = super().get_serializer_context()
        claim = get_object_or_404(Claim, pk=self.kwargs["claim_id"])
        ctx["claim"] = claim
        ctx["actor"] = _actor_from_request(self.request)
        return ctx

    def perform_create(self, serializer):
        """Execute domain behaviour and store created object for response."""
        try:
            self.created_object = serializer.save()
        except services.DomainRuleViolation as exc:
            # Convert domain rule errors into 400 responses for now.
            raise ValidationError({"detail": str(exc)}) from exc

    def create(self, request, *args, **kwargs):
        """Return the created document in a stable read contract."""
        response = super().create(request, *args, **kwargs)
        doc: ClaimDocument | None = getattr(self, "created_object", None)
        if doc is not None:
            response.data = ClaimDocumentSerializer(
                doc, context=self.get_serializer_context()
            ).data
        return response


class ClaimNoteCreateAPIView(CreateAPIView):
    """Create an internal note for a claim.

    Contract:
    - POST /api/claims/{id}/notes/
    """

    serializer_class = InternalNoteCreateSerializer
    lookup_url_kwarg = "claim_id"

    def get_serializer_context(self):
        """Provide claim and actor to serializer."""
        ctx = super().get_serializer_context()
        claim = get_object_or_404(Claim, pk=self.kwargs["claim_id"])
        ctx["claim"] = claim
        ctx["actor"] = _actor_from_request(self.request)
        return ctx

    def perform_create(self, serializer):
        """Create note via domain service."""
        try:
            self.created_object = serializer.save()
        except services.DomainRuleViolation as exc:
            raise ValidationError({"detail": str(exc)}) from exc

    def create(self, request, *args, **kwargs):
        """Return created note using the read contract."""
        response = super().create(request, *args, **kwargs)
        note: InternalNote | None = getattr(self, "created_object", None)
        if note is not None:
            response.data = InternalNoteSerializer(note).data
        return response


class ClaimDecisionCreateAPIView(CreateAPIView):
    """Record a decision for a claim.

    Contract:
    - POST /api/claims/{id}/decisions/
    """

    serializer_class = ReviewDecisionCreateSerializer
    lookup_url_kwarg = "claim_id"

    def get_serializer_context(self):
        """Provide claim and actor to serializer."""
        ctx = super().get_serializer_context()
        claim = get_object_or_404(Claim, pk=self.kwargs["claim_id"])
        ctx["claim"] = claim
        ctx["actor"] = _actor_from_request(self.request)
        return ctx

    def perform_create(self, serializer):
        """Create decision via domain service."""
        try:
            self.created_object = serializer.save()
        except services.DomainRuleViolation as exc:
            raise ValidationError({"detail": str(exc)}) from exc

    def create(self, request, *args, **kwargs):
        """Return created decision using the read contract."""
        response = super().create(request, *args, **kwargs)
        decision: ReviewDecision | None = getattr(self, "created_object", None)
        if decision is not None:
            response.data = ReviewDecisionSerializer(decision).data
        return response
