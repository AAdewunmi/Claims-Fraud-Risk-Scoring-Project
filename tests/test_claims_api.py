# path: policylens/tests/test_claims_api.py
"""
Integration tests for the canonical claim API contract.

Week 2 adds end-to-end workflow tests across nested endpoints.
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
def test_post_claim_creates_claim_and_audit_event(api_client):
    """POST /api/claims/ persists a claim and appends a CLAIM_CREATED audit event."""
    user = User.objects.create_user(username="basic-1", password="password123")
    api_client.force_authenticate(user=user)

    policy = PolicyFactory(policy_number="PL-7777")
    url = reverse("claims-list-create")

    payload = {
        "policy_id": policy.pk,
        "claim_type": Claim.Type.CLAIM,
        "priority": Claim.Priority.HIGH,
        "summary": "Broken window after storm.",
    }

    resp = api_client.post(url, data=payload, format="json")
    assert resp.status_code == 201, resp.content

    body = resp.json()
    assert body["policy_number"] == "PL-7777"
    assert body["status"] == Claim.Status.NEW
    assert body["priority"] == Claim.Priority.HIGH

    claim_id = body["id"]
    assert Claim.objects.filter(pk=claim_id).exists()
    assert AuditEvent.objects.filter(
        claim_id=claim_id,
        event_type="CLAIM_CREATED",
    ).exists()


@pytest.mark.django_db
def test_post_claim_sets_created_by_and_audit_actor_from_authenticated_user(api_client):
    """Authenticated POST /api/claims/ uses username as actor and persists evidence."""
    user = User.objects.create_user(username="reviewer-1", password="password123")

    api_client.force_authenticate(user=user)

    policy = PolicyFactory(policy_number="PL-8888")
    url = reverse("claims-list-create")

    payload = {
        "policy_id": policy.pk,
        "claim_type": Claim.Type.CLAIM,
        "priority": Claim.Priority.NORMAL,
        "summary": "Water damage in kitchen.",
    }

    resp = api_client.post(url, data=payload, format="json")
    assert resp.status_code == 201, resp.content

    body = resp.json()
    claim_id = body["id"]

    assert body["created_by"] == "reviewer-1"
    assert Claim.objects.filter(pk=claim_id, created_by="reviewer-1").exists()

    event = AuditEvent.objects.filter(
        claim_id=claim_id,
        event_type="CLAIM_CREATED",
    ).first()
    assert event is not None
    assert event.actor == "reviewer-1"


@pytest.mark.django_db
def test_get_claims_filters_by_status_and_priority(api_client):
    """GET /api/claims/?status=&priority= filters deterministically."""
    user = User.objects.create_user(username="basic-2", password="password123")
    api_client.force_authenticate(user=user)

    ClaimFactory(status=Claim.Status.NEW, priority=Claim.Priority.NORMAL)
    ClaimFactory(status=Claim.Status.IN_REVIEW, priority=Claim.Priority.HIGH)
    ClaimFactory(status=Claim.Status.IN_REVIEW, priority=Claim.Priority.NORMAL)

    url = reverse("claims-list-create")

    resp = api_client.get(
        url,
        data={
            "status": Claim.Status.IN_REVIEW,
            "priority": Claim.Priority.NORMAL,
        },
    )
    assert resp.status_code == 200

    results = resp.json()
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["status"] == Claim.Status.IN_REVIEW
    assert results[0]["priority"] == Claim.Priority.NORMAL


@pytest.mark.django_db
def test_end_to_end_claim_workflow_create_upload_note_decide(api_client):
    """Full workflow: create claim, upload document, add note, record decision, assert evidence."""
    user = User.objects.create_user(username="reviewer1", password="password123")
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    user.groups.add(reviewer_group)
    api_client.force_authenticate(user=user)

    policy = PolicyFactory(policy_number="PL-2001")

    # Create claim
    create_url = reverse("claims-list-create")
    create_payload = {
        "policy_id": policy.pk,
        "claim_type": Claim.Type.CLAIM,
        "priority": Claim.Priority.HIGH,
        "summary": "Storm damage claim.",
    }
    create_resp = api_client.post(create_url, data=create_payload, format="json")
    assert create_resp.status_code == 201, create_resp.content
    claim_id = create_resp.json()["id"]

    # Upload document
    doc_url = reverse("claims-documents-create", kwargs={"claim_id": claim_id})
    uploaded = SimpleUploadedFile(
        "photo.jpg",
        b"binarydata",
        content_type="image/jpeg",
    )
    doc_payload = {
        "file": uploaded,
        "original_filename": "photo.jpg",
        "content_type": "image/jpeg",
    }
    doc_resp = api_client.post(doc_url, data=doc_payload, format="multipart")
    assert doc_resp.status_code == 201, doc_resp.content

    # Add note
    note_url = reverse("claims-notes-create", kwargs={"claim_id": claim_id})
    note_resp = api_client.post(
        note_url, data={"body": "Reviewed initial evidence."}, format="json"
    )
    assert note_resp.status_code == 201, note_resp.content

    # Record decision
    decision_url = reverse("claims-decisions-create", kwargs={"claim_id": claim_id})
    decision_resp = api_client.post(
        decision_url,
        data={
            "decision": ReviewDecision.Decision.APPROVE,
            "notes": "Sufficient evidence.",
        },
        format="json",
    )
    assert decision_resp.status_code == 201, decision_resp.content

    # Assert claim status moved to DECIDED
    detail_url = reverse("claims-retrieve", kwargs={"claim_id": claim_id})
    detail_resp = api_client.get(detail_url)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["status"] == Claim.Status.DECIDED

    # Assert evidence exists
    assert AuditEvent.objects.filter(claim_id=claim_id, event_type="CLAIM_CREATED").exists()
    assert AuditEvent.objects.filter(claim_id=claim_id, event_type="DOCUMENT_UPLOADED").exists()
    assert AuditEvent.objects.filter(claim_id=claim_id, event_type="NOTE_ADDED").exists()
    assert AuditEvent.objects.filter(claim_id=claim_id, event_type="DECISION_RECORDED").exists()
