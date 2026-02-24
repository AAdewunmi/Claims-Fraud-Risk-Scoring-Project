# path: policylens/tests/test_claims_audit_api.py
"""
Integration tests for audit events API.

Sprint 2 ensures audit events are queryable evidence for ops workflows.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from policylens.apps.claims.models import Claim, ReviewDecision
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_audit_events_endpoint_returns_expected_event_types(api_client):
    """Audit listing should include event types created by workflow actions."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    reviewer = User.objects.create_user(username="reviewer_audit", password="password123")
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
            "summary": "Audit test claim.",
        },
        format="json",
    )
    assert create_resp.status_code == 201
    claim_id = create_resp.json()["id"]

    note_url = reverse("claims-notes-create", kwargs={"claim_id": claim_id})
    note_resp = api_client.post(note_url, data={"body": "Audit note."}, format="json")
    assert note_resp.status_code == 201

    decision_url = reverse("claims-decisions-create", kwargs={"claim_id": claim_id})
    decision_resp = api_client.post(
        decision_url,
        data={"decision": ReviewDecision.Decision.REQUEST_INFO, "notes": "Need more docs."},
        format="json",
    )
    assert decision_resp.status_code == 201

    audit_url = reverse("claims-audit-events", kwargs={"claim_id": claim_id})
    audit_resp = api_client.get(audit_url)
    assert audit_resp.status_code == 200

    events = audit_resp.json()
    event_types = {e["event_type"] for e in events}
    assert "CLAIM_CREATED" in event_types
    assert "NOTE_ADDED" in event_types
    assert "DECISION_RECORDED" in event_types
