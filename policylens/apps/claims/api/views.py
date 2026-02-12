# path: policylens/apps/claims/api/views.py
"""API views for claims."""

from __future__ import annotations

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
from policylens.apps.claims.models import (
    Claim,
    ClaimDocument,
    InternalNote,
    ReviewDecision,
)
from policylens.apps.claims.permissions import IsReviewerOrAdmin
from policylens.apps.core.idempotency import (
    IdempotencyConflict,
    find_record,
    request_hash_from_bytes,
    store_record,
)


def _actor_from_request(request) -> str:
    """Return a stable actor id for audit events."""
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return user.get_username() or str(user.pk)
    return "anonymous"


def _domain_error_to_validation_error(
    exc: services.DomainRuleViolation,
) -> ValidationError:
    """Convert domain rule violations into a stable client-facing error response."""
    return ValidationError({"detail": str(exc)})


class ClaimListCreateAPIView(ListCreateAPIView):
    """List and create claims.

    Supports idempotency via Idempotency-Key header on create.
    """

    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]

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

    def perform_create(self, serializer):
        """Create claim via domain service and store created object."""
        try:
            self.created_object = serializer.save()
        except services.DomainRuleViolation as exc:
            raise _domain_error_to_validation_error(exc) from exc

    def create(self, request, *args, **kwargs):
        """Create claim with idempotency support."""
        key = request.headers.get("Idempotency-Key")
        if key:
            body_hash = request_hash_from_bytes(request.body or b"")
            existing = find_record(
                user=request.user,
                key=key,
                method=request.method,
                path=request.path,
            )
            if existing is not None:
                if existing.request_hash != body_hash:
                    return Response(
                        {"detail": "Idempotency key reuse with different payload."},
                        status=409,
                    )
                return Response(existing.response_body, status=existing.response_status)

        response = super().create(request, *args, **kwargs)

        if key:
            body_hash = request_hash_from_bytes(request.body or b"")
            try:
                store_record(
                    user=request.user,
                    key=key,
                    method=request.method,
                    path=request.path,
                    request_hash=body_hash,
                    response_status=response.status_code,
                    response_body=(
                        response.data
                        if isinstance(response.data, dict)
                        else {"result": response.data}
                    ),
                )
            except IdempotencyConflict:
                return Response(
                    {"detail": "Idempotency key reuse with different payload."},
                    status=409,
                )

        return response


class ClaimRetrieveAPIView(RetrieveAPIView):
    """Retrieve claim detail."""

    serializer_class = ClaimDetailSerializer
    lookup_url_kwarg = "claim_id"
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Annotate counts used by ops views and include ml_score relation."""
        return (
            Claim.objects.select_related("policy", "ml_score")
            .annotate(
                documents_count=Count("documents", distinct=True),
                notes_count=Count("notes", distinct=True),
                decisions_count=Count("decisions", distinct=True),
            )
            .all()
        )


class ClaimDocumentUploadAPIView(CreateAPIView):
    """Upload a document for a claim."""

    serializer_class = ClaimDocumentUploadSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
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
            raise _domain_error_to_validation_error(exc) from exc

    def create(self, request, *args, **kwargs):
        """Return the created document in a stable read contract."""
        key = request.headers.get("Idempotency-Key")
        if key:
            body_hash = request_hash_from_bytes(request.body or b"")
            existing = find_record(
                user=request.user,
                key=key,
                method=request.method,
                path=request.path,
            )
            if existing is not None:
                if existing.request_hash != body_hash:
                    return Response(
                        {"detail": "Idempotency key reuse with different payload."},
                        status=409,
                    )
                return Response(existing.response_body, status=existing.response_status)

        response = super().create(request, *args, **kwargs)
        doc: ClaimDocument | None = getattr(self, "created_object", None)
        if doc is not None:
            response.data = ClaimDocumentSerializer(
                doc,
                context=self.get_serializer_context(),
            ).data

        if key:
            body_hash = request_hash_from_bytes(request.body or b"")
            try:
                store_record(
                    user=request.user,
                    key=key,
                    method=request.method,
                    path=request.path,
                    request_hash=body_hash,
                    response_status=response.status_code,
                    response_body=(
                        response.data
                        if isinstance(response.data, dict)
                        else {"result": response.data}
                    ),
                )
            except IdempotencyConflict:
                return Response(
                    {"detail": "Idempotency key reuse with different payload."},
                    status=409,
                )

        return response


class ClaimNoteCreateAPIView(CreateAPIView):
    """Create an internal note for a claim."""

    serializer_class = InternalNoteCreateSerializer
    permission_classes = [IsAuthenticated]
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
            raise _domain_error_to_validation_error(exc) from exc

    def create(self, request, *args, **kwargs):
        """Return created note using the read contract."""
        key = request.headers.get("Idempotency-Key")
        if key:
            body_hash = request_hash_from_bytes(request.body or b"")
            existing = find_record(
                user=request.user,
                key=key,
                method=request.method,
                path=request.path,
            )
            if existing is not None:
                if existing.request_hash != body_hash:
                    return Response(
                        {"detail": "Idempotency key reuse with different payload."},
                        status=409,
                    )
                return Response(existing.response_body, status=existing.response_status)

        response = super().create(request, *args, **kwargs)
        note: InternalNote | None = getattr(self, "created_object", None)
        if note is not None:
            response.data = InternalNoteSerializer(note).data

        if key:
            body_hash = request_hash_from_bytes(request.body or b"")
            try:
                store_record(
                    user=request.user,
                    key=key,
                    method=request.method,
                    path=request.path,
                    request_hash=body_hash,
                    response_status=response.status_code,
                    response_body=(
                        response.data
                        if isinstance(response.data, dict)
                        else {"result": response.data}
                    ),
                )
            except IdempotencyConflict:
                return Response(
                    {"detail": "Idempotency key reuse with different payload."},
                    status=409,
                )

        return response


class ClaimDecisionCreateAPIView(CreateAPIView):
    """Record a decision for a claim.

    Decisions are restricted to reviewer or admin roles.

    Supports idempotency via Idempotency-Key header.
    """

    serializer_class = ReviewDecisionCreateSerializer
    permission_classes = [IsAuthenticated, IsReviewerOrAdmin]
    lookup_url_kwarg = "claim_id"

    def get_serializer_context(self):
        """Provide claim and actor to serializer."""
        ctx = super().get_serializer_context()
        claim = get_object_or_404(Claim, pk=self.kwargs["claim_id"])
        ctx["claim"] = claim
        ctx["actor"] = _actor_from_request(self.request)
        return ctx

    def create(self, request, *args, **kwargs):
        """Create decision with idempotency support."""
        key = request.headers.get("Idempotency-Key")
        if key:
            body_hash = request_hash_from_bytes(request.body or b"")
            existing = find_record(
                user=request.user,
                key=key,
                method=request.method,
                path=request.path,
            )
            if existing is not None:
                if existing.request_hash != body_hash:
                    return Response(
                        {"detail": "Idempotency key reuse with different payload."},
                        status=409,
                    )
                return Response(existing.response_body, status=existing.response_status)

        try:
            response = super().create(request, *args, **kwargs)
        except services.DomainRuleViolation as exc:
            raise _domain_error_to_validation_error(exc) from exc

        decision: ReviewDecision | None = getattr(self, "created_object", None)
        if decision is not None:
            response.data = ReviewDecisionSerializer(decision).data

        if key:
            body_hash = request_hash_from_bytes(request.body or b"")
            try:
                store_record(
                    user=request.user,
                    key=key,
                    method=request.method,
                    path=request.path,
                    request_hash=body_hash,
                    response_status=response.status_code,
                    response_body=(
                        response.data
                        if isinstance(response.data, dict)
                        else {"result": response.data}
                    ),
                )
            except IdempotencyConflict:
                return Response(
                    {"detail": "Idempotency key reuse with different payload."},
                    status=409,
                )

        return response

    def perform_create(self, serializer):
        """Create decision via domain service and keep object for response."""
        self.created_object = serializer.save()
