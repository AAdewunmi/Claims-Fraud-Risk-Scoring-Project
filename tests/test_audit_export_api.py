# path: policylens/tests/test_audit_export_api.py
"""
Integration test for audit export endpoint.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from policylens.apps.claims.models import Claim
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_audit_export_contains_expected_sections_and_ordering(api_client):
    """Audit export should include stable sections and chronological ordering for events."""
    user = User.objects.create_user(username="export_user", password="password123")
    api_client.force_authenticate(user=user)

    policy = PolicyFactory()
    create_url = reverse("claims-list-create")
    claim_resp = api_client.post(
        create_url,
        data={
            "policy_id": policy.pk,
            "claim_type": Claim.Type.CLAIM,
            "priority": Claim.Priority.NORMAL,
            "summary": "Export test",
        },
        format="json",
    )
    assert claim_resp.status_code == 201
    claim_id = claim_resp.json()["id"]

    doc_url = reverse("claims-documents-create", kwargs={"claim_id": claim_id})
    uploaded = SimpleUploadedFile("evidence.txt", b"hello", content_type="text/plain")
    doc_resp = api_client.post(
        doc_url,
        data={"file": uploaded, "original_filename": "evidence.txt", "content_type": "text/plain"},
        format="multipart",
    )
    assert doc_resp.status_code == 201

    note_url = reverse("claims-notes-create", kwargs={"claim_id": claim_id})
    note_resp = api_client.post(note_url, data={"body": "First note"}, format="json")
    assert note_resp.status_code == 201

    # Decisions require reviewer/admin in your project. We skip creation here to
    # keep export test focused on shape.

    export_url = reverse("claims-audit-export", kwargs={"claim_id": claim_id})
    export_resp = api_client.get(export_url)
    assert export_resp.status_code == 200

    body = export_resp.json()
    assert body["export_version"] == "v1"
    assert "claim" in body
    assert "policy" in body
    assert "policy_holder" in body
    assert "sla_clock" in body
    assert "documents" in body
    assert "notes" in body
    assert "audit_events" in body

    # Documents should be a list with our uploaded doc.
    assert len(body["documents"]) == 1
    assert body["documents"][0]["original_filename"] == "evidence.txt"

    # Notes should be a list with our note.
    assert len(body["notes"]) == 1
    assert body["notes"][0]["body"] == "First note"

    # Audit events should include SLA_STARTED at least, and be chronological.
    events = body["audit_events"]
    assert len(events) >= 2
    created_times = [e["created_at"] for e in events]
    assert created_times == sorted(created_times)
