"""Tests for admin governance model string representations."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from policylens.apps.core.models import (
    AdminAuditLog,
    AdminHealthCheck,
    AdminOperationalSetting,
    IdempotencyRecord,
)

pytestmark = pytest.mark.django_db


def test_core_model_string_representations_cover_admin_governance_models():
    User = get_user_model()
    user = User.objects.create_user(username="model-user", password="password123")

    idempotency = IdempotencyRecord.objects.create(
        key="idempo-key",
        user=user,
        method="POST",
        path="/api/claims/",
        request_hash="abc123",
        response_status=201,
        response_body={"ok": True},
    )
    assert str(idempotency) == "IdempotencyRecord(idempo-key, POST /api/claims/)"

    setting = AdminOperationalSetting.objects.create(
        key="UI_PAGE_SIZE",
        value="15",
        value_type=AdminOperationalSetting.ValueType.INTEGER,
        description="Page size",
        updated_by=user,
    )
    assert str(setting) == "UI_PAGE_SIZE=15"

    audit = AdminAuditLog.objects.create(
        actor=user,
        event_type=AdminAuditLog.EventType.CONFIG_UPDATED,
        setting_key="UI_PAGE_SIZE",
        message="Changed page size",
        metadata={"old": "10", "new": "15"},
    )
    audit_text = str(audit)
    assert "CONFIG_UPDATED by model-user at " in audit_text

    health = AdminHealthCheck.objects.create(
        status="ok",
        details={"database": {"status": "ok"}},
        checked_by=user,
    )
    health_text = str(health)
    assert "HealthCheck(status=ok, checked_at=" in health_text
