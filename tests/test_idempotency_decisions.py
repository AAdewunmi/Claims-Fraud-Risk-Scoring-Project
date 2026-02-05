# path: policylens/tests/test_idempotency_decisions.py
"""
Integration tests for decision idempotency behaviour.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from policylens.apps.claims.models import AuditEvent, Claim, ReviewDecision
from tests.factories import ClaimFactory, PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_decision_idempotency_replay_returns_same_response_and_no_duplicate_audit(
    api_client,
):
    """Replaying a decision request with same Idempotency-Key should be safe."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    reviewer = User.objects.create_user(
        username="idem_reviewer",
        password="password123",
    )
    reviewer.groups.add(reviewer_group)
    api_client.force_authenticate(user=reviewer)

    policy = PolicyFactory()
    create_url = reverse("claims-list-create")
    create_resp = api_client.post(
        create_url,
        data={
            "policy_id": policy.pk,
            "claim_type": Claim.Type.CLAIM,
            "priority": Claim.Priority.NORMAL,
            "summary": "Idempotency claim",
        },
        format="json",
    )
    assert create_resp.status_code == 201
    claim_id = create_resp.json()["id"]

    decision_url = reverse("claims-decisions-create", kwargs={"claim_id": claim_id})
    headers = {"HTTP_IDEMPOTENCY_KEY": "key-123"}

    first = api_client.post(
        decision_url,
        data={
            "decision": ReviewDecision.Decision.REQUEST_INFO,
            "notes": "Need more docs.",
        },
        format="json",
        **headers,
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = api_client.post(
        decision_url,
        data={
            "decision": ReviewDecision.Decision.REQUEST_INFO,
            "notes": "Need more docs.",
        },
        format="json",
        **headers,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first_id

    assert (
        AuditEvent.objects.filter(
            claim_id=claim_id,
            event_type="DECISION_RECORDED",
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_decision_idempotency_conflict_on_payload_mismatch_returns_409(api_client):
    """Same Idempotency-Key with different payload should return 409."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    reviewer = User.objects.create_user(
        username="idem_reviewer2",
        password="password123",
    )
    reviewer.groups.add(reviewer_group)
    api_client.force_authenticate(user=reviewer)

    policy = PolicyFactory()
    create_url = reverse("claims-list-create")
    claim_resp = api_client.post(
        create_url,
        data={
            "policy_id": policy.pk,
            "claim_type": Claim.Type.CLAIM,
            "priority": Claim.Priority.NORMAL,
        },
        format="json",
    )
    assert claim_resp.status_code == 201
    claim_id = claim_resp.json()["id"]

    decision_url = reverse("claims-decisions-create", kwargs={"claim_id": claim_id})
    headers = {"HTTP_IDEMPOTENCY_KEY": "key-xyz"}

    ok = api_client.post(
        decision_url,
        data={"decision": ReviewDecision.Decision.REQUEST_INFO, "notes": "First"},
        format="json",
        **headers,
    )
    assert ok.status_code == 201

    conflict = api_client.post(
        decision_url,
        data={"decision": ReviewDecision.Decision.APPROVE, "notes": "Different"},
        format="json",
        **headers,
    )
    assert conflict.status_code == 409
    assert "detail" in conflict.json()


@pytest.mark.django_db
def test_claim_create_idempotency_replay_returns_same_response_and_no_duplicate_audit(
    api_client,
):
    """Replaying claim creation with same Idempotency-Key should be safe."""
    user = User.objects.create_user(username="idem_claim_user", password="password123")
    api_client.force_authenticate(user=user)

    policy = PolicyFactory()
    create_url = reverse("claims-list-create")
    headers = {"HTTP_IDEMPOTENCY_KEY": "claim-key-1"}

    payload = {
        "policy_id": policy.pk,
        "claim_type": Claim.Type.CLAIM,
        "priority": Claim.Priority.NORMAL,
        "summary": "Idempotency claim create",
    }

    first = api_client.post(create_url, data=payload, format="json", **headers)
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = api_client.post(create_url, data=payload, format="json", **headers)
    assert second.status_code == 201
    assert second.json()["id"] == first_id

    assert Claim.objects.count() == 1
    assert (
        AuditEvent.objects.filter(
            claim_id=first_id,
            event_type="CLAIM_CREATED",
        ).count()
        == 1
    )
    assert (
        AuditEvent.objects.filter(
            claim_id=first_id,
            event_type="SLA_STARTED",
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_claim_create_idempotency_conflict_on_payload_mismatch_returns_409(api_client):
    """Same Idempotency-Key with different payload should return 409."""
    user = User.objects.create_user(username="idem_claim_user2", password="password123")
    api_client.force_authenticate(user=user)

    policy = PolicyFactory()
    create_url = reverse("claims-list-create")
    headers = {"HTTP_IDEMPOTENCY_KEY": "claim-key-2"}

    ok = api_client.post(
        create_url,
        data={
            "policy_id": policy.pk,
            "claim_type": Claim.Type.CLAIM,
            "priority": Claim.Priority.NORMAL,
            "summary": "First",
        },
        format="json",
        **headers,
    )
    assert ok.status_code == 201

    conflict = api_client.post(
        create_url,
        data={
            "policy_id": policy.pk,
            "claim_type": Claim.Type.CLAIM,
            "priority": Claim.Priority.HIGH,
            "summary": "Different",
        },
        format="json",
        **headers,
    )
    assert conflict.status_code == 409
    assert "detail" in conflict.json()


@pytest.mark.django_db
def test_document_upload_idempotency_replay_returns_same_response(api_client):
    """Replaying a document upload with same Idempotency-Key should be safe."""
    user = User.objects.create_user(username="idem_doc_user", password="password123")
    api_client.force_authenticate(user=user)

    claim = ClaimFactory()
    doc_url = reverse("claims-documents-create", kwargs={"claim_id": claim.pk})
    headers = {"HTTP_IDEMPOTENCY_KEY": "doc-key-1"}

    uploaded = SimpleUploadedFile("photo.jpg", b"binarydata", content_type="image/jpeg")
    payload = {
        "file": uploaded,
        "original_filename": "photo.jpg",
        "content_type": "image/jpeg",
    }

    first = api_client.post(doc_url, data=payload, format="multipart", **headers)
    assert first.status_code == 201
    first_id = first.json()["id"]

    uploaded_again = SimpleUploadedFile(
        "photo.jpg",
        b"binarydata",
        content_type="image/jpeg",
    )
    second = api_client.post(
        doc_url,
        data={
            "file": uploaded_again,
            "original_filename": "photo.jpg",
            "content_type": "image/jpeg",
        },
        format="multipart",
        **headers,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first_id

    assert (
        AuditEvent.objects.filter(
            claim_id=claim.pk,
            event_type="DOCUMENT_UPLOADED",
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_document_upload_idempotency_conflict_on_payload_mismatch_returns_409(
    api_client,
):
    """Same Idempotency-Key with different payload should return 409."""
    user = User.objects.create_user(username="idem_doc_user2", password="password123")
    api_client.force_authenticate(user=user)

    claim = ClaimFactory()
    doc_url = reverse("claims-documents-create", kwargs={"claim_id": claim.pk})
    headers = {"HTTP_IDEMPOTENCY_KEY": "doc-key-2"}

    uploaded = SimpleUploadedFile("photo.jpg", b"binarydata", content_type="image/jpeg")
    ok = api_client.post(
        doc_url,
        data={
            "file": uploaded,
            "original_filename": "photo.jpg",
            "content_type": "image/jpeg",
        },
        format="multipart",
        **headers,
    )
    assert ok.status_code == 201

    uploaded_diff = SimpleUploadedFile(
        "photo.jpg",
        b"different",
        content_type="image/jpeg",
    )
    conflict = api_client.post(
        doc_url,
        data={
            "file": uploaded_diff,
            "original_filename": "photo.jpg",
            "content_type": "image/jpeg",
        },
        format="multipart",
        **headers,
    )
    assert conflict.status_code == 409
    assert "detail" in conflict.json()


@pytest.mark.django_db
def test_note_create_idempotency_replay_returns_same_response_and_no_duplicate_audit(
    api_client,
):
    """Replaying a note create with same Idempotency-Key should be safe."""
    user = User.objects.create_user(username="idem_note_user", password="password123")
    api_client.force_authenticate(user=user)

    claim = ClaimFactory()
    note_url = reverse("claims-notes-create", kwargs={"claim_id": claim.pk})
    headers = {"HTTP_IDEMPOTENCY_KEY": "note-key-1"}

    first = api_client.post(
        note_url,
        data={"body": "Reviewed."},
        format="json",
        **headers,
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = api_client.post(
        note_url,
        data={"body": "Reviewed."},
        format="json",
        **headers,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first_id

    assert (
        AuditEvent.objects.filter(
            claim_id=claim.pk,
            event_type="NOTE_ADDED",
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_note_create_idempotency_conflict_on_payload_mismatch_returns_409(
    api_client,
):
    """Same Idempotency-Key with different payload should return 409."""
    user = User.objects.create_user(username="idem_note_user2", password="password123")
    api_client.force_authenticate(user=user)

    claim = ClaimFactory()
    note_url = reverse("claims-notes-create", kwargs={"claim_id": claim.pk})
    headers = {"HTTP_IDEMPOTENCY_KEY": "note-key-2"}

    ok = api_client.post(note_url, data={"body": "First"}, format="json", **headers)
    assert ok.status_code == 201

    conflict = api_client.post(
        note_url,
        data={"body": "Different"},
        format="json",
        **headers,
    )
    assert conflict.status_code == 409
    assert "detail" in conflict.json()
