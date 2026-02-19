# path: policylens/apps/ops/views_htmx.py
"""
HTMX endpoints for ops claim actions.

These are server-rendered partial responses.
They call domain services directly to avoid duplicating workflow logic.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from policylens.apps.claims import services
from policylens.apps.claims.ml.scoring import ModelNotReady, score_claim
from policylens.apps.claims.models import Claim
from policylens.apps.ops.forms import AddNoteForm


def _actor(request: HttpRequest) -> str:
    """Return actor id for audit events."""
    return request.user.get_username() or str(request.user.pk)


@login_required
def htmx_add_note(request: HttpRequest, claim_id: int) -> HttpResponse:
    """Add a note and return refreshed notes partial."""
    claim = get_object_or_404(Claim, pk=claim_id)
    form = AddNoteForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        services.add_note(claim=claim, body=form.cleaned_data["body"], actor=_actor(request))
        claim.refresh_from_db()

    claim = Claim.objects.prefetch_related("notes").get(pk=claim_id)
    return render(
        request, "ops/partials/notes_list.html", context={"claim": claim, "form": AddNoteForm()}
    )


@login_required
def htmx_score_claim(request: HttpRequest, claim_id: int) -> HttpResponse:
    """Score claim and return refreshed ML card partial."""
    claim = get_object_or_404(Claim, pk=claim_id)
    error = None
    if request.method == "POST":
        try:
            score_claim(claim=claim, actor=_actor(request))
        except ModelNotReady as exc:
            error = str(exc)

    claim = Claim.objects.select_related("ml_score").get(pk=claim_id)
    return render(request, "ops/partials/ml_card.html", context={"claim": claim, "error": error})
