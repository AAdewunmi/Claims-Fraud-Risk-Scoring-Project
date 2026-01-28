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

from apps.claims.models import Claim, ReviewDecision
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_unauthenticated_requests_are_rejected(api_client):
    """Core endpoints should return 401 for unauthenticated requests."""
    policy = PolicyFactory()
    url = reverse("claims-list-create")
    resp = api_client.post(
        url,
        data={"policy_id": policy.pk, "claim_type": Claim.Type.CLAIM, "priority": Claim.Priority.NORMAL},
        format="json",
    )
    assert resp.status_code == 401