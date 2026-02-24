"""
DB-hitting tests for surface-specific login entry points.

The goal is to prove:
- each login page renders
- posting valid credentials logs in
- redirect is deterministic per surface
- failed credentials keep user unauthenticated
"""

import pytest
from django.contrib.auth import SESSION_KEY, get_user_model
from django.urls import reverse

from policylens.apps.accounts.views import SURFACE_INTENT_SESSION_KEY

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user_password():
    return "pass-12345-strong"


@pytest.fixture()
def basic_user(user_password):
    User = get_user_model()
    return User.objects.create_user(username="alex", password=user_password)


@pytest.mark.parametrize(
    "surface, login_url_name, console_url_name",
    [
        ("admin", "accounts:login_admin", "accounts:console_admin"),
        ("reviewer", "accounts:login_reviewer", "accounts:console_reviewer"),
        ("customer", "accounts:login_customer", "accounts:console_customer"),
    ],
)
def test_surface_login_get_renders(client, surface, login_url_name, console_url_name):
    del console_url_name
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
        ("reviewer", "accounts:login_reviewer", "accounts:console_reviewer"),
        ("customer", "accounts:login_customer", "accounts:console_customer"),
    ],
)
def test_surface_login_post_redirects_to_console(
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
