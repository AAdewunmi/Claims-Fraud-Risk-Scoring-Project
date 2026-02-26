"""
Contract-focused tests for ops queue view helpers.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from policylens.apps.ops import views

User = get_user_model()


@pytest.mark.django_db
def test_ops_queue_forbidden_for_authenticated_wrong_role(client):
    """Authenticated users without reviewer/admin role should receive 403."""
    user = User.objects.create_user(username="ops_non_reviewer", password="password123")
    client.force_login(user)

    response = client.get(reverse("ops:queue"))

    assert response.status_code == 403
    assert any(template.name == "site/forbidden.html" for template in response.templates)


def test_apply_optional_filters_returns_input_when_queryset_has_no_model(rf):
    """Filter helper should no-op when a queryset-like object has no model attr."""
    request = rf.get("/ops/queue/", data={"status": "NEW"})
    value = [1, 2, 3]

    assert views._apply_optional_filters(request, value) is value


def test_apply_stable_ordering_returns_input_when_queryset_has_no_model():
    """Ordering helper should no-op when a queryset-like object has no model attr."""
    value = [1, 2, 3]

    assert views._apply_stable_ordering(value) is value


def test_apply_stable_ordering_appends_id_tiebreaker_when_missing(monkeypatch):
    """Ordering helper should append id if available and not already selected."""

    class DummyQuerySet:
        def __init__(self) -> None:
            self.model = object()
            self.ordered_with: tuple[str, ...] | None = None

        def order_by(self, *fields: str):
            self.ordered_with = fields
            return self

    checks = iter([False, False, False, False, True])

    def fake_model_has_field(_model, _field_name: str) -> bool:
        return next(checks)

    monkeypatch.setattr(views, "_model_has_field", fake_model_has_field)

    qs = DummyQuerySet()
    result = views._apply_stable_ordering(qs)

    assert result is qs
    assert qs.ordered_with == ("id",)
