# path: policylens/tests/test_claims_api_validation.py
"""
Validation and negative behaviour tests for PolicyLens API.

Week 2 validates:
- Document upload constraints
- Workflow rule failures return stable errors
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from policylens.apps.claims.models import Claim, ReviewDecision
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_document_upload_rejects_unsupported_content_type(api_client):
    """Uploading an unsupported content type should return 400."""
    user = User.objects.create_user(username="reviewer_v1", password="password123")
    api_client.force_authenticate(user=user)

    policy = PolicyFactory()
    create_url = reverse("claims-list-create")
    create_resp = api_client.post(
        create_url,
        data={
            "policy_id": policy.pk,
            "claim_type": Claim.Type.CLAIM,
            "priority": Claim.Priority.NORMAL,
            "summary": "Test claim.",
        },
        format="json",
    )
    assert create_resp.status_code == 201
    claim_id = create_resp.json()["id"]

    doc_url = reverse("claims-documents-create", kwargs={"claim_id": claim_id})
    uploaded = SimpleUploadedFile("script.exe", b"data", content_type="application/octet-stream")
    resp = api_client.post(
        doc_url,
        data={"file": uploaded, "original_filename": "script.exe", "content_type": "application/octet-stream"},
        format="multipart",
    )
    assert resp.status_code == 400
    assert "content_type" in resp.json()

@pytest.mark.django_db
def test_decision_after_decided_returns_400(api_client):
    """Once decided, recording a second decision should return 400 with a clear detail message."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    reviewer = User.objects.create_user(username="reviewer_v2", password="password123")
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
            "summary": "Ready to decide.",
        },
        format="json",
    )
    assert create_resp.status_code == 201
    claim_id = create_resp.json()["id"]

    decision_url = reverse("claims-decisions-create", kwargs={"claim_id": claim_id})
    first = api_client.post(
        decision_url,
        data={"decision": ReviewDecision.Decision.APPROVE, "notes": "Approved."},
        format="json",
    )
    assert first.status_code == 201

    second = api_client.post(
        decision_url,
        data={"decision": ReviewDecision.Decision.REQUEST_INFO, "notes": "Too late."},
        format="json",
    )
    assert second.status_code == 400
    assert second.json().get("detail")
