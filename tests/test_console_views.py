"""Tests for role-based console views."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse


@pytest.mark.django_db
def test_admin_console_redirects_anonymous_to_admin_login(client):
    admin_home = reverse("console:admin_home")
    response = client.get(admin_home, follow=False)
    assert response.status_code == 302
    assert response["Location"] == f"{reverse('accounts:login_admin')}?next={admin_home}"


@pytest.mark.django_db
def test_admin_console_renders_context_links_for_admin_group_user(client):
    admin_group = Group.objects.create(name="admin")
    User = get_user_model()
    user = User.objects.create_user(username="console-admin", password="password123")
    user.groups.add(admin_group)
    client.force_login(user)

    response = client.get(reverse("console:admin_home"))

    assert response.status_code == 200
    assert response.context["django_admin_url"] == reverse("admin:index")
    assert response.context["reviewer_console_url"] == reverse("console:reviewer_home")
    assert response.context["customer_console_url"] == reverse("console:customer_home")


@pytest.mark.django_db
def test_reviewer_console_denies_authenticated_non_reviewer(client):
    customer_group = Group.objects.create(name="customer")
    User = get_user_model()
    user = User.objects.create_user(username="console-customer", password="password123")
    user.groups.add(customer_group)
    client.force_login(user)

    response = client.get(reverse("console:reviewer_home"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_reviewer_console_allows_reviewer_group_user(client):
    reviewer_group = Group.objects.create(name="reviewer")
    User = get_user_model()
    user = User.objects.create_user(username="console-reviewer", password="password123")
    user.groups.add(reviewer_group)
    client.force_login(user)

    response = client.get(reverse("console:reviewer_home"))

    assert response.status_code == 200
    assert b"Reviewer queue" in response.content


@pytest.mark.django_db
def test_customer_console_allows_customer_group_user(client):
    customer_group = Group.objects.create(name="customer")
    User = get_user_model()
    user = User.objects.create_user(username="console-customer-ok", password="password123")
    user.groups.add(customer_group)
    client.force_login(user)

    response = client.get(reverse("console:customer_home"))

    assert response.status_code == 200
    assert b"My claims" in response.content
