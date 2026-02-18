# path: policylens/tests/test_ops_claim_detail.py
"""
UI tests for ops claim detail page.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from policylens.apps.claims.models import AuditEvent, Claim, SlaClock
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_ops_claim_detail_renders_sections(client):
    """Claim detail page should render core sections."""
    user = User.objects.create_user(username="ops_user4", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="Hello",
        created_by="seed",
        status=Claim.Status.NEW,
    )
    SlaClock.objects.create(
        claim=claim, started_at=claim.created_at, due_at=timezone.now() + timedelta(days=1)
    )
    AuditEvent.objects.create(
        claim=claim, event_type="CLAIM_CREATED", actor="seed", payload={"x": 1}
    )

    url = reverse("ops:claim-detail", kwargs={"claim_id": claim.id})
    resp = client.get(url)
    assert resp.status_code == 200

    html = resp.content.decode("utf-8")
    assert f"Claim #{claim.id}" in html
    assert "SLA" in html
    assert "ML completeness" in html
    assert "Documents" in html
    assert "Notes" in html
    assert "Decisions" in html
    assert "Audit timeline" in html
