# path: policylens/tests/test_ops_htmx_note.py
"""
HTMX integration test: add note flow.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from policylens.apps.claims.models import Claim
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_htmx_add_note_creates_note_and_returns_partial(client):
    """Posting a note via HTMX endpoint should create a note and return updated notes HTML."""
    user = User.objects.create_user(username="ops_htmx_user", password="password123")
    client.force_login(user)

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="HTMX",
        created_by="seed",
        status=Claim.Status.NEW,
    )

    url = reverse("ops:htmx-add-note", kwargs={"claim_id": claim.id})
    resp = client.post(url, data={"body": "First note"}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200

    claim.refresh_from_db()
    assert claim.notes.count() == 1
    assert "First note" in resp.content.decode("utf-8")
