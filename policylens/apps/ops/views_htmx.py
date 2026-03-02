"""
HTMX endpoints for ops claim actions.

Friday adds:
- Document upload partial
- Decision recording partial
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from policylens.apps.claims import services
from policylens.apps.claims.ml.scoring import ModelNotReady, score_claim
from policylens.apps.claims.models import Claim, ReviewDecision
from policylens.apps.core.authz import user_has_reviewer_write_access, user_is_admin
from policylens.apps.ops.forms import AddNoteForm, DecisionForm

SURFACE_INTENT_SESSION_KEY = "policylens_surface_intent"
SURFACE_ADMIN = "admin"


def _actor(request: HttpRequest) -> str:
    """Return actor id for audit events."""
    return request.user.get_username() or str(request.user.pk)


def _reviewer_write_enabled(request: HttpRequest) -> bool:
    """
    Return True when reviewer write actions are enabled for this request.

    Admin login intent (`/login/admin/`) always forces read-only mode on reviewer
    surfaces, even if the user also has reviewer privileges.
    """
    session = getattr(request, "session", None)
    surface_intent = session.get(SURFACE_INTENT_SESSION_KEY) if session is not None else None
    if user_is_admin(request.user):
        if surface_intent == SURFACE_ADMIN:
            return False
        return user_has_reviewer_write_access(request.user)
    return True


@login_required
def htmx_add_note(request: HttpRequest, claim_id: int) -> HttpResponse:
    """Add a note and return refreshed notes partial."""
    claim = get_object_or_404(Claim, pk=claim_id)
    form = AddNoteForm(request.POST or None)
    read_only = not _reviewer_write_enabled(request)
    error = None

    if request.method == "POST" and read_only:
        error = "Read-only view. Admin users cannot add notes from reviewer console."
    elif request.method == "POST" and form.is_valid():
        services.add_note(claim=claim, body=form.cleaned_data["body"], actor=_actor(request))

    claim = Claim.objects.prefetch_related("notes").get(pk=claim_id)
    response = render(
        request,
        "ops/partials/notes_list.html",
        context={"claim": claim, "form": AddNoteForm(), "read_only": read_only, "error": error},
    )
    if request.method == "POST" and read_only:
        response.status_code = 403
    return response


@login_required
def htmx_score_claim(request: HttpRequest, claim_id: int) -> HttpResponse:
    """Score claim and return refreshed ML card partial."""
    claim = get_object_or_404(Claim, pk=claim_id)
    error = None
    read_only = not _reviewer_write_enabled(request)
    if request.method == "POST" and read_only:
        error = "Read-only view. Admin users cannot score claims from reviewer console."
    elif request.method == "POST":
        try:
            score_claim(claim=claim, actor=_actor(request))
        except ModelNotReady as exc:
            error = str(exc)

    claim = Claim.objects.select_related("ml_score").get(pk=claim_id)
    response = render(
        request,
        "ops/partials/ml_card.html",
        context={"claim": claim, "error": error, "read_only": read_only},
    )
    if request.method == "POST" and read_only:
        response.status_code = 403
    return response


@login_required
def htmx_upload_document(request: HttpRequest, claim_id: int) -> HttpResponse:
    """Upload a document and return refreshed documents partial."""
    claim = get_object_or_404(Claim, pk=claim_id)
    error = None
    read_only = not _reviewer_write_enabled(request)

    if request.method == "POST" and read_only:
        error = "Read-only view. Admin users cannot upload documents from reviewer console."
    elif request.method == "POST":
        f: UploadedFile | None = request.FILES.get("file")
        original_filename = (request.POST.get("original_filename") or "").strip()
        content_type = (
            request.POST.get("content_type") or (getattr(f, "content_type", "") if f else "") or ""
        ).strip()

        if f is None:
            error = "File is required."
        elif not original_filename:
            error = "Original filename is required."
        else:
            try:
                services.add_document(
                    claim=claim,
                    uploaded_file=f,
                    original_filename=original_filename,
                    content_type=content_type,
                    actor=_actor(request),
                )
            except services.DomainRuleViolation as exc:
                error = str(exc)

    claim = Claim.objects.prefetch_related("documents").get(pk=claim_id)
    response = render(
        request,
        "ops/partials/documents_table.html",
        context={"claim": claim, "error": error, "read_only": read_only},
    )
    if request.method == "POST" and read_only:
        response.status_code = 403
    return response


@login_required
def htmx_add_decision(request: HttpRequest, claim_id: int) -> HttpResponse:
    """Record a decision and return refreshed decisions partial."""
    claim = get_object_or_404(Claim, pk=claim_id)
    form = DecisionForm(request.POST or None)
    read_only = not _reviewer_write_enabled(request)
    error = None

    if request.method == "POST" and read_only:
        error = "Read-only view. Admin users cannot record decisions from reviewer console."
    elif request.method == "POST" and form.is_valid():
        try:
            services.add_decision(
                claim=claim,
                decision=form.cleaned_data["decision"],
                notes=form.cleaned_data.get("notes") or "",
                actor=_actor(request),
            )
            form = DecisionForm()
        except services.DomainRuleViolation as exc:
            form.add_error(None, str(exc))

    claim = Claim.objects.prefetch_related(
        Prefetch("decisions", queryset=ReviewDecision.objects.order_by("-decided_at"))
    ).get(pk=claim_id)
    response = render(
        request,
        "ops/partials/decisions_list.html",
        context={"claim": claim, "form": form, "read_only": read_only, "error": error},
    )
    if request.method == "POST" and read_only:
        response.status_code = 403
    return response
