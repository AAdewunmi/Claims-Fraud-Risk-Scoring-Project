# path: policylens/tests/test_ops_htmx_note.py
"""
HTMX integration test: add note flow.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.urls import reverse

from policylens.apps.claims import services
from policylens.apps.claims.ml.scoring import ModelNotReady
from policylens.apps.claims.models import Claim, ReviewDecision
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


@pytest.mark.django_db
def test_htmx_upload_document_success_creates_doc_and_renders_partial(client):
    """Posting document upload should create document and return documents partial."""
    user = User.objects.create_user(username="ops_htmx_user_doc", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX upload",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    url = reverse("ops:htmx-upload-document", kwargs={"claim_id": claim.id})
    upload = SimpleUploadedFile("invoice.pdf", b"pdf-bytes", content_type="application/pdf")
    resp = client.post(
        url,
        data={"file": upload, "original_filename": "invoice.pdf"},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    claim.refresh_from_db()
    assert claim.documents.count() == 1
    html = resp.content.decode("utf-8")
    assert "Documents" in html
    assert "invoice.pdf" in html


@pytest.mark.django_db
def test_htmx_upload_document_missing_file_returns_error_context(client, monkeypatch):
    """Missing file should not create a document and should set a validation error."""
    user = User.objects.create_user(username="ops_htmx_user_doc_err", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX upload error",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    captured = {}

    def fake_render(request, template_name, context):
        captured["template_name"] = template_name
        captured["context"] = context
        return HttpResponse("ok")

    monkeypatch.setattr(views_htmx, "render", fake_render)

    url = reverse("ops:htmx-upload-document", kwargs={"claim_id": claim.id})
    resp = client.post(url, data={"original_filename": "missing.pdf"}, HTTP_HX_REQUEST="true")

    assert resp.status_code == 200
    claim.refresh_from_db()
    assert claim.documents.count() == 0
    assert captured["template_name"] == "ops/partials/documents_table.html"
    assert captured["context"]["error"] == "File is required."


@pytest.mark.django_db
def test_htmx_upload_document_domain_rule_violation_sets_error(client, monkeypatch):
    """Domain rule failures should be rendered as upload error context."""
    user = User.objects.create_user(username="ops_htmx_user_doc_rule", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX upload rule",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    captured = {}

    def fake_add_document(**kwargs):
        raise services.DomainRuleViolation("Claim is already decided.")

    def fake_render(request, template_name, context):
        captured["template_name"] = template_name
        captured["context"] = context
        return HttpResponse("ok")

    monkeypatch.setattr(views_htmx.services, "add_document", fake_add_document)
    monkeypatch.setattr(views_htmx, "render", fake_render)

    url = reverse("ops:htmx-upload-document", kwargs={"claim_id": claim.id})
    upload = SimpleUploadedFile("invoice.pdf", b"pdf-bytes", content_type="application/pdf")
    resp = client.post(
        url,
        data={"file": upload, "original_filename": "invoice.pdf"},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    assert captured["template_name"] == "ops/partials/documents_table.html"
    assert captured["context"]["error"] == "Claim is already decided."


@pytest.mark.django_db
def test_htmx_add_decision_success_creates_decision(client):
    """Posting a decision should create a decision and return decisions partial."""
    user = User.objects.create_user(username="ops_htmx_user_decision", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX decision",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    url = reverse("ops:htmx-add-decision", kwargs={"claim_id": claim.id})
    resp = client.post(
        url,
        data={"decision": ReviewDecision.Decision.REQUEST_INFO, "notes": "Need docs"},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    claim.refresh_from_db()
    assert claim.decisions.count() == 1
    html = resp.content.decode("utf-8")
    assert "Decisions" in html


@pytest.mark.django_db
def test_htmx_add_decision_domain_rule_violation_sets_error(client, monkeypatch):
    """Domain rule failures should be returned as form non-field errors."""
    user = User.objects.create_user(username="ops_htmx_user_decision_rule", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX decision rule",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    captured = {}

    def fake_add_decision(**kwargs):
        raise services.DomainRuleViolation("Claim is already decided.")

    def fake_render(request, template_name, context):
        captured["template_name"] = template_name
        captured["context"] = context
        return HttpResponse("ok")

    monkeypatch.setattr(views_htmx.services, "add_decision", fake_add_decision)
    monkeypatch.setattr(views_htmx, "render", fake_render)

    url = reverse("ops:htmx-add-decision", kwargs={"claim_id": claim.id})
    resp = client.post(
        url,
        data={"decision": ReviewDecision.Decision.APPROVE, "notes": "Approve now"},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    assert captured["template_name"] == "ops/partials/decisions_list.html"
    form = captured["context"]["form"]
    assert form.data["decision"] == ReviewDecision.Decision.APPROVE
    assert form.data["notes"] == "Approve now"
    assert form.non_field_errors() == ["Claim is already decided."]


@pytest.mark.django_db
def test_htmx_add_decision_returns_decisions_in_reverse_decided_at_order(client, monkeypatch):
    """Rendered decision history should be sorted by newest decision first."""
    user = User.objects.create_user(username="ops_htmx_user_decision_order", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX decision history order",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    services.add_decision(
        claim=claim,
        decision=ReviewDecision.Decision.REQUEST_INFO,
        notes="First decision",
        actor=user.username,
    )
    services.add_decision(
        claim=claim,
        decision=ReviewDecision.Decision.REQUEST_INFO,
        notes="Second decision",
        actor=user.username,
    )

    captured = {}

    def fake_render(request, template_name, context):
        captured["template_name"] = template_name
        captured["context"] = context
        return HttpResponse("ok")

    monkeypatch.setattr(views_htmx, "render", fake_render)

    url = reverse("ops:htmx-add-decision", kwargs={"claim_id": claim.id})
    resp = client.get(url, HTTP_HX_REQUEST="true")

    assert resp.status_code == 200
    assert captured["template_name"] == "ops/partials/decisions_list.html"
    decisions = list(captured["context"]["claim"].decisions.all())
    assert len(decisions) == 2
    assert decisions[0].notes == "Second decision"
    assert decisions[1].notes == "First decision"
