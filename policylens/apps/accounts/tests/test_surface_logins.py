"""
DB-hitting tests for surface-specific login entry points and first boundary guard.

Proof targets:
- each login page renders
- posting valid credentials logs in
- redirect is deterministic per surface
- reviewer console enforces boundary rules:
  - anonymous -> redirect to /login/reviewer/ with next
  - authenticated wrong role -> 403
  - reviewer/admin group -> 200
"""

from unittest.mock import Mock

import pytest
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.test import RequestFactory
from django.urls import reverse

from policylens.apps.accounts.views import (
    SURFACE_INTENT_SESSION_KEY,
    ConsolePlaceholderView,
    SurfaceLoginView,
    user_has_reviewer_surface_access,
)

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user_password():
    return "pass-12345-strong"


@pytest.fixture()
def reviewer_group():
    return Group.objects.create(name="reviewer")


@pytest.fixture()
def admin_group():
    return Group.objects.create(name="admin")


@pytest.fixture()
def basic_user(user_password):
    User = get_user_model()
    return User.objects.create_user(username="alex", password=user_password)


@pytest.fixture()
def reviewer_user(user_password, reviewer_group):
    User = get_user_model()
    user = User.objects.create_user(username="riley", password=user_password)
    user.groups.add(reviewer_group)
    return user


@pytest.fixture()
def admin_user(user_password, admin_group):
    User = get_user_model()
    user = User.objects.create_user(username="sam", password=user_password)
    user.groups.add(admin_group)
    return user


@pytest.mark.parametrize(
    "surface, login_url_name",
    [
        ("admin", "accounts:login_admin"),
        ("reviewer", "accounts:login_reviewer"),
        ("customer", "accounts:login_customer"),
    ],
)
def test_surface_login_get_renders(client, surface, login_url_name):
    response = client.get(reverse(login_url_name))
    assert response.status_code == 200
    assert b"Sign in" in response.content
    assert response.context["surface"] == surface
    assert response.context["surface_title"] == f"{surface.capitalize()} login"
    assert client.session[SURFACE_INTENT_SESSION_KEY] == surface


@pytest.mark.parametrize(
    "surface, login_url_name, console_url_name",
    [
        ("admin", "accounts:login_admin", "accounts:console_admin"),
        ("customer", "accounts:login_customer", "accounts:console_customer"),
    ],
)
def test_surface_login_post_redirects_to_console_non_guarded_surfaces(
    client, basic_user, user_password, surface, login_url_name, console_url_name
):
    response = client.post(
        reverse(login_url_name),
        data={"username": basic_user.username, "password": user_password},
        follow=False,
    )
    assert response.status_code == 302
    assert response["Location"] == reverse(console_url_name)
    assert response.wsgi_request.user.is_authenticated
    assert client.session[SESSION_KEY] == str(basic_user.pk)
    assert client.session[SURFACE_INTENT_SESSION_KEY] == surface

    follow_response = client.get(reverse(console_url_name))
    assert follow_response.status_code == 200
    assert b"placeholder" in follow_response.content.lower()


def test_reviewer_console_anonymous_redirects_to_reviewer_login_with_next(client):
    console_url = reverse("accounts:console_reviewer")
    login_url = reverse("accounts:login_reviewer")
    response = client.get(console_url, follow=False)
    assert response.status_code == 302
    assert response["Location"] == f"{login_url}?next={console_url}"


def test_surface_login_get_with_safe_next_sets_context_and_hidden_input(client):
    console_url = reverse("accounts:console_reviewer")
    response = client.get(f"{reverse('accounts:login_reviewer')}?next={console_url}")
    assert response.status_code == 200
    assert response.context["next"] == console_url
    assert f'name="next" value="{console_url}"'.encode() in response.content


def test_reviewer_console_authenticated_wrong_role_gets_403(client, basic_user, user_password):
    login_response = client.post(
        reverse("accounts:login_customer"),
        data={"username": basic_user.username, "password": user_password},
        follow=False,
    )
    assert login_response.status_code == 302

    response = client.get(reverse("accounts:console_reviewer"))
    assert response.status_code == 403
    assert b"Forbidden" in response.content


@pytest.mark.parametrize("include_query_next", [False, True])
def test_reviewer_console_allows_reviewer_group(
    client, reviewer_user, user_password, include_query_next
):
    console_url = reverse("accounts:console_reviewer")
    login_url = reverse("accounts:login_reviewer")
    if include_query_next:
        login_url = f"{login_url}?next={console_url}"

    response = client.post(
        login_url,
        data={"username": reviewer_user.username, "password": user_password, "next": console_url},
        follow=False,
    )
    assert response.status_code == 302
    assert response["Location"] == console_url
    assert client.session[SURFACE_INTENT_SESSION_KEY] == "reviewer"

    console_response = client.get(console_url)
    assert console_response.status_code == 200
    assert b"reviewer console" in console_response.content.lower()


def test_reviewer_console_allows_admin_group(client, admin_user, user_password):
    console_url = reverse("accounts:console_reviewer")
    login_url = f"{reverse('accounts:login_reviewer')}?next={console_url}"
    response = client.post(
        login_url,
        data={"username": admin_user.username, "password": user_password, "next": console_url},
        follow=False,
    )
    assert response.status_code == 302
    assert response["Location"] == console_url

    console_response = client.get(console_url)
    assert console_response.status_code == 200
    assert b"reviewer console" in console_response.content.lower()


def test_user_has_reviewer_surface_access_denies_anonymous():
    assert user_has_reviewer_surface_access(AnonymousUser()) is False


def test_user_has_reviewer_surface_access_allows_superuser(user_password):
    User = get_user_model()
    superuser = User.objects.create_superuser(
        username="root",
        email="root@example.com",
        password=user_password,
    )
    assert user_has_reviewer_surface_access(superuser) is True


@pytest.mark.parametrize(
    "surface, login_url_name",
    [
        ("admin", "accounts:login_admin"),
        ("reviewer", "accounts:login_reviewer"),
        ("customer", "accounts:login_customer"),
    ],
)
def test_surface_login_post_invalid_credentials_shows_form_error(
    client, basic_user, surface, login_url_name
):
    response = client.post(
        reverse(login_url_name),
        data={"username": basic_user.username, "password": "incorrect-password"},
        follow=False,
    )
    assert response.status_code == 200
    assert response.wsgi_request.user.is_anonymous
    assert response.context["form"].non_field_errors()
    assert SESSION_KEY not in client.session
    assert client.session[SURFACE_INTENT_SESSION_KEY] == surface


def test_surface_login_as_view_rejects_unknown_surface():
    with pytest.raises(ValueError, match="Unknown surface 'unknown'"):
        SurfaceLoginView.as_view(surface="unknown")


def test_console_placeholder_as_view_rejects_unknown_surface():
    with pytest.raises(ValueError, match="Unknown surface 'unknown'"):
        ConsolePlaceholderView.as_view(surface="unknown")


def test_surface_login_form_valid_returns_bad_request_when_user_is_missing():
    view = SurfaceLoginView()
    view.surface = "admin"
    view.request = RequestFactory().post(reverse("accounts:login_admin"))
    form = Mock()
    form.get_user.return_value = None

    response = view.form_valid(form)

    assert response.status_code == 400
    assert response.content == b"Login failed."
