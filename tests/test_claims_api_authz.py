# path: policylens/tests/test_claims_api_authz.py
"""
Authorization and authentication tests for PolicyLens API.

Week 2 verifies:
- Unauthenticated requests are rejected by default
- Decisions require reviewer or admin role
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
def test_unauthenticated_requests_are_rejected(api_client):
    """Core endpoints should return 401 for unauthenticated requests."""
    policy = PolicyFactory()
    url = reverse("claims-list-create")
    resp = api_client.post(
        url,
        data={
            "policy_id": policy.pk,
            "claim_type": Claim.Type.CLAIM,
            "priority": Claim.Priority.NORMAL,
        },
        format="json",
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_decision_requires_reviewer_or_admin(api_client):
    """Decision endpoint should return 403 for authenticated users without reviewer/admin role."""
    user = User.objects.create_user(username="basic1", password="password123")
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

    decision_url = reverse("claims-decisions-create", kwargs={"claim_id": claim_id})
    decision_resp = api_client.post(
        decision_url,
        data={"decision": ReviewDecision.Decision.APPROVE, "notes": "Attempted."},
        format="json",
    )
    assert decision_resp.status_code == 403


@pytest.mark.django_db
def test_reviewer_can_record_decision(api_client):
    """Reviewer group member should be allowed to record decisions."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    reviewer = User.objects.create_user(username="reviewer2", password="password123")
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
            "summary": "Test claim.",
        },
        format="json",
    )
    assert create_resp.status_code == 201
    claim_id = create_resp.json()["id"]

    decision_url = reverse("claims-decisions-create", kwargs={"claim_id": claim_id})
    decision_resp = api_client.post(
        decision_url,
        data={"decision": ReviewDecision.Decision.REJECT, "notes": "Rejected."},
        format="json",
    )
    assert decision_resp.status_code == 201
