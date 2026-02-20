# path: policylens/tests/test_ops_htmx_decision.py
"""
HTMX integration test: decision flow.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from policylens.apps.claims.models import Claim, ReviewDecision
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_htmx_add_decision_creates_decision_and_returns_partial(client):
    """Posting a decision via HTMX endpoint should create a decision and return updated HTML."""
    user = User.objects.create_user(username="ops_decider", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="Decision",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    url = reverse("ops:htmx-add-decision", kwargs={"claim_id": claim.id})
    resp = client.post(
        url,
        data={"decision": ReviewDecision.Decision.REQUEST_INFO, "notes": "Need more evidence"},
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200

    claim.refresh_from_db()
    assert claim.decisions.count() == 1
    assert "Decisions" in resp.content.decode("utf-8")
