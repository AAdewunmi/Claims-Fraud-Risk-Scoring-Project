"""
Ops UI views for PolicyLens.

Week 6 contract additions:
- Reviewer surface is role-gated (reviewer or admin).
- Reviewer queue list is paginated at 15 per page.
- Pagination uses stable ordering and preserves filters in links.

This module keeps the queue as a server-rendered surface with deterministic behaviour.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from policylens.apps.claims.models import (
    AuditEvent,
    Claim,
    ClaimDocument,
    InternalNote,
    ReviewDecision,
)
from policylens.apps.core.authz import user_is_reviewer
from policylens.apps.core.pagination import paginate_request_queryset
from policylens.apps.ops.forms import AddNoteForm, DecisionForm


@login_required
def ops_home(request: HttpRequest) -> HttpResponse:
    """Redirect ops landing to queue."""
    return redirect("ops:queue")


def _model_has_field(model: Any, field_name: str) -> bool:
    """Return True if a Django model has a given field name."""
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _apply_optional_filters(request: HttpRequest, qs: Any) -> Any:
    """
    Apply filter query params to a queryset where the underlying model supports them.

    This keeps the queue view resilient while the domain model evolves.
    """
    model = getattr(qs, "model", None)
    if model is None:
        return qs

    candidates = {
        "status": request.GET.get("status"),
        "sla_state": request.GET.get("sla_state") or request.GET.get("sla"),
        "priority": request.GET.get("priority"),
    }

    for field_name, raw_value in candidates.items():
        if raw_value is None or raw_value == "":
            continue
        if not _model_has_field(model, field_name):
            continue
        qs = qs.filter(**{field_name: raw_value})

    return qs


def _apply_stable_ordering(qs: Any) -> Any:
    """
    Apply stable ordering explicitly.

    We include `id` as a final tiebreaker so ordering is deterministic even when
    higher-priority fields are equal.
    """
    model = getattr(qs, "model", None)
    if model is None:
        return qs

    preferred = [
        "-priority",
        "sla_due_at",
        "-created_at",
        "id",
    ]

    order_fields: list[str] = []
    for field_name in preferred:
        raw = field_name.lstrip("-")
        if _model_has_field(model, raw):
            order_fields.append(field_name)

    if "id" not in [field_name.lstrip("-") for field_name in order_fields] and _model_has_field(
        model, "id"
    ):
        order_fields.append("id")

    return qs.order_by(*order_fields) if order_fields else qs


@login_required
@require_GET
def ops_queue(request: HttpRequest) -> HttpResponse:
    """
    Reviewer queue surface.

    Access
    - Anonymous users should reach this through reviewer login flows.
    - Authenticated wrong-role users get a clean 403.

    Pagination
    - page param 1-indexed
    - page size from settings.UI_PAGE_SIZE
    - invalid page -> page 1
    - out of range -> last page
    - filters preserved in links
    """
    if not user_is_reviewer(request.user):
        return render(request, "site/forbidden.html", status=403)

    qs = Claim.objects.all()
    qs = _apply_optional_filters(request, qs)
    qs = _apply_stable_ordering(qs)

    pagination = paginate_request_queryset(
        request,
        qs,
        page_size=getattr(settings, "UI_PAGE_SIZE", 15),
    )

    return render(
        request,
        "ops/queue.html",
        {
            "page_title": "Review queue",
            "pagination": pagination,
            "claims": pagination.page_obj.object_list,
            "items": pagination.page_obj.object_list,
            "filters": {
                "status": request.GET.get("status", ""),
                "priority": request.GET.get("priority", ""),
                "sla": request.GET.get("sla", ""),
                "sla_state": request.GET.get("sla_state", ""),
            },
        },
    )


# Backward-compatible name for existing URL imports/routes.
queue_view = ops_queue


@login_required
def claim_detail_view(request: HttpRequest, claim_id: int) -> HttpResponse:
    """Render claim detail page with timeline sections."""
    claim = get_object_or_404(
        Claim.objects.select_related(
            "policy", "policy__holder", "sla_clock", "ml_score"
        ).prefetch_related(
            Prefetch("documents", queryset=ClaimDocument.objects.order_by("uploaded_at")),
            Prefetch("notes", queryset=InternalNote.objects.order_by("created_at")),
            Prefetch("decisions", queryset=ReviewDecision.objects.order_by("-decided_at")),
            Prefetch("audit_events", queryset=AuditEvent.objects.order_by("created_at")),
        ),
        pk=claim_id,
    )

    return render(
        request,
        "ops/claim_detail.html",
        context={
            "page_title": f"Claim #{claim.id}",
            "claim": claim,
            "note_form": AddNoteForm(),
            "decision_form": DecisionForm(),
        },
    )
