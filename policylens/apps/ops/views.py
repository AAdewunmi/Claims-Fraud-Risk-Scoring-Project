# path: policylens/apps/ops/views.py
"""
Ops views (server-rendered).

Week 5:
- Queue view reuses domain queue builder.
- Claim detail page lands Wednesday.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from policylens.apps.claims.models import (
    AuditEvent,
    Claim,
    ClaimDocument,
    InternalNote,
    ReviewDecision,
)
from policylens.apps.claims.queue import build_queue_queryset


@login_required
def ops_home(request: HttpRequest) -> HttpResponse:
    """Redirect ops landing to queue."""
    return redirect("ops:queue")


@login_required
def queue_view(request: HttpRequest) -> HttpResponse:
    """Render review queue using the same ordering rules as the API."""
    status = request.GET.get("status") or None
    priority = request.GET.get("priority") or None
    sla_filter = request.GET.get("sla") or None

    items = list(build_queue_queryset(status=status, priority=priority, sla_filter=sla_filter))
    for idx, obj in enumerate(items, start=1):
        setattr(obj, "queue_rank", idx)

    return render(
        request,
        "ops/queue.html",
        context={
            "page_title": "Review queue",
            "items": items,
            "filters": {"status": status or "", "priority": priority or "", "sla": sla_filter or ""},
        },
    )


@login_required
def claim_detail_view(request: HttpRequest, claim_id: int) -> HttpResponse:
    """Claim detail placeholder. Full content lands Wednesday."""
    claim = get_object_or_404(
        Claim.objects.select_related("policy", "policy__holder", "sla_clock", "ml_score").prefetch_related(
            Prefetch(
                "documents",
                queryset=ClaimDocument.objects.order_by("-uploaded_at"),
            ),
            Prefetch(
                "notes",
                queryset=InternalNote.objects.order_by("-created_at"),
            ),
            Prefetch(
                "decisions",
                queryset=ReviewDecision.objects.order_by("-decided_at"),
            ),
            Prefetch(
                "audit_events",
                queryset=AuditEvent.objects.order_by("-created_at"),
            ),
        ),
        pk=claim_id,
    )
    return render(request, "ops/claim_detail.html", context={"claim": claim})
