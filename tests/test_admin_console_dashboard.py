"""Integration tests for the admin governance dashboard."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from policylens.apps.core.models import AdminAuditLog, AdminHealthCheck, AdminOperationalSetting

pytestmark = pytest.mark.django_db


def _create_role_groups() -> dict[str, Group]:
    return {
        "admin": Group.objects.create(name="admin"),
        "reviewer": Group.objects.create(name="reviewer"),
        "customer": Group.objects.create(name="customer"),
    }


def _create_admin_user(username: str = "admin-user"):
    User = get_user_model()
    admin_group, _ = Group.objects.get_or_create(name="admin")
    user = User.objects.create_user(username=username, password="password123")
    user.groups.add(admin_group)
    return user


def test_admin_dashboard_renders_governance_sections(client):
    admin_user = _create_admin_user()
    client.force_login(admin_user)

    response = client.get(reverse("console:admin_home"))

    assert response.status_code == 200
    assert b"User and role management" in response.content
    assert b"Configuration management" in response.content
    assert b"Audit oversight" in response.content
    assert b"Health and ops controls" in response.content


def test_admin_user_management_paginates_five_per_page(client):
    admin_user = _create_admin_user()
    User = get_user_model()
    for idx in range(8):
        User.objects.create_user(username=f"paged-user-{idx:02d}", password="password123")

    client.force_login(admin_user)

    page_one = client.get(reverse("console:admin_home"), data={"q": "paged-user-"})
    assert page_one.status_code == 200
    assert len(page_one.context["managed_users"]) == 5
    assert page_one.context["users_pagination"].paginator.per_page == 5
    assert page_one.context["users_pagination"].page_obj.number == 1
    assert b"paged-user-00" in page_one.content
    assert b"paged-user-04" in page_one.content
    assert b"paged-user-05" not in page_one.content
    assert "users_page=2" in page_one.context["users_pagination"].next_url

    page_two = client.get(
        reverse("console:admin_home"),
        data={"q": "paged-user-", "users_page": "2"},
    )
    assert page_two.status_code == 200
    assert len(page_two.context["managed_users"]) == 3
    assert page_two.context["users_pagination"].page_obj.number == 2
    assert b"paged-user-05" in page_two.content
    assert b"paged-user-07" in page_two.content
    assert b"paged-user-00" not in page_two.content


def test_admin_can_update_roles_and_access_and_is_audited(client):
    groups = _create_role_groups()
    admin_user = _create_admin_user()
    User = get_user_model()
    target_user = User.objects.create_user(username="target-user", password="password123")
    target_user.groups.add(groups["reviewer"])
    target_user.is_active = True
    target_user.save(update_fields=["is_active"])

    client.force_login(admin_user)
    response = client.post(
        reverse("console:admin_user_update", kwargs={"user_id": target_user.id}),
        data={
            "groups": ["admin", "customer"],
            # omit `is_active` to assert deactivation path
        },
        follow=False,
    )

    assert response.status_code == 302
    target_user.refresh_from_db()
    assert target_user.is_active is False
    assert set(target_user.groups.values_list("name", flat=True)) == {"admin", "customer"}
    assert AdminAuditLog.objects.filter(
        event_type=AdminAuditLog.EventType.USER_ROLE_UPDATED,
        target_user=target_user,
    ).exists()
    assert AdminAuditLog.objects.filter(
        event_type=AdminAuditLog.EventType.USER_ACCESS_UPDATED,
        target_user=target_user,
    ).exists()


def test_non_admin_is_forbidden_from_admin_write_endpoints(client):
    _create_role_groups()
    User = get_user_model()
    reviewer_group = Group.objects.get(name="reviewer")
    actor = User.objects.create_user(username="reviewer-user", password="password123")
    actor.groups.add(reviewer_group)
    target = User.objects.create_user(username="target-user", password="password123")

    client.force_login(actor)
    response = client.post(
        reverse("console:admin_user_update", kwargs={"user_id": target.id}),
        data={"groups": ["customer"], "is_active": "on"},
    )

    assert response.status_code == 403
    assert b"Forbidden" in response.content
    assert AdminAuditLog.objects.count() == 0


def test_admin_setting_upsert_validates_and_tracks_history(client):
    admin_user = _create_admin_user()
    client.force_login(admin_user)

    response_ok = client.post(
        reverse("console:admin_setting_upsert"),
        data={"key": "UI_PAGE_SIZE", "value": "20"},
        follow=False,
    )
    assert response_ok.status_code == 302

    setting = AdminOperationalSetting.objects.get(key="UI_PAGE_SIZE")
    assert setting.value == "20"
    assert setting.value_type == AdminOperationalSetting.ValueType.INTEGER
    assert setting.updated_by == admin_user
    assert AdminAuditLog.objects.filter(
        event_type=AdminAuditLog.EventType.CONFIG_UPDATED,
        setting_key="UI_PAGE_SIZE",
    ).exists()

    response_invalid = client.post(
        reverse("console:admin_setting_upsert"),
        data={"key": "UI_PAGE_SIZE", "value": "1000"},
        follow=True,
    )
    assert response_invalid.status_code == 200
    setting.refresh_from_db()
    assert setting.value == "20"
    assert b"must be between 5 and 100" in response_invalid.content


def test_admin_health_run_stores_snapshot_and_logs_audit(client, monkeypatch):
    admin_user = _create_admin_user()
    client.force_login(admin_user)

    monkeypatch.setattr(
        "policylens.apps.console.views.check_database",
        lambda: (False, "OperationalError"),
    )

    response = client.post(reverse("console:admin_health_run"), follow=True)

    assert response.status_code == 200
    health_check = AdminHealthCheck.objects.get()
    assert health_check.status == "error"
    assert health_check.details["database"]["status"] == "error"
    assert health_check.details["database"]["error"] == "OperationalError"
    assert AdminAuditLog.objects.filter(event_type=AdminAuditLog.EventType.HEALTH_CHECKED).exists()
    assert b"Latest status:" in response.content


def test_admin_audit_feed_filters_and_detail_view_work(client):
    admin_user = _create_admin_user()
    User = get_user_model()
    other_actor = User.objects.create_user(username="ops-admin", password="password123")

    kept_event = AdminAuditLog.objects.create(
        actor=other_actor,
        event_type=AdminAuditLog.EventType.CONFIG_UPDATED,
        message="Updated UI page size.",
        metadata={"new_value": "30"},
    )
    AdminAuditLog.objects.create(
        actor=admin_user,
        event_type=AdminAuditLog.EventType.USER_ROLE_UPDATED,
        message="Changed role membership.",
    )

    client.force_login(admin_user)

    response = client.get(
        reverse("console:admin_home"),
        data={"actor": "ops", "event_type": AdminAuditLog.EventType.CONFIG_UPDATED},
    )
    assert response.status_code == 200
    assert b"Updated UI page size." in response.content
    assert b"Changed role membership." not in response.content

    detail = client.get(reverse("console:admin_audit_detail", kwargs={"event_id": kept_event.id}))
    assert detail.status_code == 200
    assert b"Admin audit event" in detail.content
    assert b"Updated UI page size." in detail.content
