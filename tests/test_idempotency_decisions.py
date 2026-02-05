# path: policylens/tests/test_idempotency_decisions.py
"""
Integration tests for decision idempotency behaviour.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from policylens.apps.claims.models import AuditEvent, Claim, ReviewDecision
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_decision_idempotency_replay_returns_same_response_and_no_duplicate_audit(api_client):
    """Replaying a decision request with same Idempotency-Key should be safe."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    reviewer = User.objects.create_user(username="idem_reviewer", password="password123")
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
        data={"decision": ReviewDecision.Decision.REQUEST_INFO, "notes": "Need more docs."},
        format="json",
        **headers,
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = api_client.post(
        decision_url,
        data={"decision": ReviewDecision.Decision.REQUEST_INFO, "notes": "Need more docs."},
        format="json",
        **headers,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first_id

    assert AuditEvent.objects.filter(claim_id=claim_id, event_type="DECISION_RECORDED").count() == 1