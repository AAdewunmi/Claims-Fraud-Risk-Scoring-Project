# path: policylens/tests/test_ops_htmx_note.py
"""
HTMX integration test: add note flow.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse

from policylens.apps.claims.ml.scoring import ModelNotReady
from policylens.apps.claims.models import Claim
from policylens.apps.ops import views_htmx
from policylens.apps.ops.forms import AddNoteForm
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_htmx_add_note_creates_note_and_returns_partial(client):
    """Posting a note via HTMX endpoint should create a note and return updated notes HTML."""
    user = User.objects.create_user(username="ops_htmx_user", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    url = reverse("ops:htmx-add-note", kwargs={"claim_id": claim.id})
    resp = client.post(url, data={"body": "First note"}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200

    claim.refresh_from_db()
    assert claim.notes.count() == 1
    assert "First note" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_htmx_add_note_rejects_blank_body(client):
    """Blank note bodies should not create notes."""
    user = User.objects.create_user(username="ops_htmx_user_blank", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX blank note",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    url = reverse("ops:htmx-add-note", kwargs={"claim_id": claim.id})
    resp = client.post(url, data={"body": "   "}, HTTP_HX_REQUEST="true")

    assert resp.status_code == 200
    claim.refresh_from_db()
    assert claim.notes.count() == 0


def test_add_note_form_clean_body_rejects_blank_value():
    """Custom clean_body validation should reject whitespace-only body."""
    form = AddNoteForm()
    form.cleaned_data = {"body": "   "}

    with pytest.raises(ValidationError):
        form.clean_body()


@pytest.mark.django_db
def test_htmx_score_claim_post_success_renders_partial(client, monkeypatch):
    """Posting score action should call scorer and render score partial."""
    user = User.objects.create_user(username="ops_htmx_user_score", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX score",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    captured = {}

    def fake_score_claim(*, claim, actor):
        captured["score_call"] = {"claim_id": claim.id, "actor": actor}

    def fake_render(request, template_name, context):
        captured["render_call"] = {"template_name": template_name, "context": context}
        return HttpResponse("ok")

    monkeypatch.setattr(views_htmx, "score_claim", fake_score_claim)
    monkeypatch.setattr(views_htmx, "render", fake_render)

    url = reverse("ops:htmx-score-claim", kwargs={"claim_id": claim.id})
    resp = client.post(url, HTTP_HX_REQUEST="true")

    assert resp.status_code == 200
    assert captured["score_call"]["claim_id"] == claim.id
    assert captured["score_call"]["actor"] == user.username
    assert captured["render_call"]["template_name"] == "ops/partials/ml_card.html"
    assert captured["render_call"]["context"]["error"] is None
    assert captured["render_call"]["context"]["claim"].id == claim.id


@pytest.mark.django_db
def test_htmx_score_claim_model_not_ready_sets_error(client, monkeypatch):
    """Model-not-ready scoring failures should render partial with error message."""
    user = User.objects.create_user(username="ops_htmx_user_score_error", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX score error",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    captured = {}

    def fake_score_claim(*, claim, actor):
        raise ModelNotReady("Model is not trained yet.")

    def fake_render(request, template_name, context):
        captured["render_call"] = {"template_name": template_name, "context": context}
        return HttpResponse("ok")

    monkeypatch.setattr(views_htmx, "score_claim", fake_score_claim)
    monkeypatch.setattr(views_htmx, "render", fake_render)

    url = reverse("ops:htmx-score-claim", kwargs={"claim_id": claim.id})
    resp = client.post(url, HTTP_HX_REQUEST="true")

    assert resp.status_code == 200
    assert captured["render_call"]["template_name"] == "ops/partials/ml_card.html"
    assert captured["render_call"]["context"]["error"] == "Model is not trained yet."
    assert captured["render_call"]["context"]["claim"].id == claim.id
