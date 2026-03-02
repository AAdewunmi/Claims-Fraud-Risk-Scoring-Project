"""Tests for temporary core authz role helpers."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group

from policylens.apps.core.authz import (
    user_has_customer_write_access,
    user_has_reviewer_write_access,
    user_in_any_group,
    user_is_admin,
    user_is_customer,
    user_is_reviewer,
)


@pytest.mark.django_db
def test_role_helpers_deny_anonymous():
    anonymous = AnonymousUser()
    assert user_is_admin(anonymous) is False
    assert user_is_reviewer(anonymous) is False
    assert user_is_customer(anonymous) is False


def test_user_in_any_group_denies_unauthenticated_user():
    assert user_in_any_group(AnonymousUser(), ["admin"]) is False


@pytest.mark.django_db
def test_role_helpers_allow_superuser():
    User = get_user_model()
    superuser = User.objects.create_superuser(
        username="authz-root",
        email="root@example.com",
        password="password123",
    )
    assert user_is_admin(superuser) is True
    assert user_is_reviewer(superuser) is True
    assert user_is_customer(superuser) is True
    assert user_has_reviewer_write_access(superuser) is True
    assert user_has_customer_write_access(superuser) is True


@pytest.mark.django_db
def test_role_helpers_allow_expected_groups_and_deny_others():
    reviewer_group = Group.objects.create(name="reviewer")
    admin_group = Group.objects.create(name="admin")
    customer_group = Group.objects.create(name="customer")
    User = get_user_model()

    plain_user = User.objects.create_user(username="plain-user", password="password123")
    reviewer_user = User.objects.create_user(username="reviewer-user", password="password123")
    reviewer_user.groups.add(reviewer_group)
    admin_user = User.objects.create_user(username="admin-user", password="password123")
    admin_user.groups.add(admin_group)
    customer_user = User.objects.create_user(username="customer-user", password="password123")
    customer_user.groups.add(customer_group)

    assert user_is_admin(plain_user) is False
    assert user_is_reviewer(plain_user) is False
    assert user_is_customer(plain_user) is False
    assert user_has_reviewer_write_access(plain_user) is False
    assert user_has_customer_write_access(plain_user) is False

    assert user_is_admin(reviewer_user) is False
    assert user_is_reviewer(reviewer_user) is True
    assert user_is_customer(reviewer_user) is False
    assert user_has_reviewer_write_access(reviewer_user) is True
    assert user_has_customer_write_access(reviewer_user) is False

    assert user_is_admin(admin_user) is True
    assert user_is_reviewer(admin_user) is True
    assert user_is_customer(admin_user) is True
    assert user_has_reviewer_write_access(admin_user) is False
    assert user_has_customer_write_access(admin_user) is False

    assert user_is_admin(customer_user) is False
    assert user_is_reviewer(customer_user) is False
    assert user_is_customer(customer_user) is True
    assert user_has_reviewer_write_access(customer_user) is False
    assert user_has_customer_write_access(customer_user) is True
