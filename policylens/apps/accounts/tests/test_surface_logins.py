"""
DB-hitting tests for surface-specific login entry points.

The goal is to prove:
- each login page renders
- posting valid credentials logs in
- redirect is deterministic per surface
"""

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user_password():
    return "pass-12345-strong"


@pytest.fixture()
def basic_user(user_password):
    User = get_user_model()
    return User.objects.create_user(username="alex", password=user_password)


@pytest.mark.parametrize(
    "login_path, console_path",
    [
        ("/login/admin/", "/console/admin/"),
        ("/login/reviewer/", "/console/reviewer/"),
        ("/login/customer/", "/console/customer/"),
    ],
)
def test_surface_login_get_renders(client, login_path, console_path):
    response = client.get(login_path)
    assert response.status_code == 200
    assert b"Sign in" in response.content


@pytest.mark.parametrize(
    "login_path, console_path",
    [
        ("/login/admin/", "/console/admin/"),
        ("/login/reviewer/", "/console/reviewer/"),
        ("/login/customer/", "/console/customer/"),
    ],
)
def test_surface_login_post_redirects_to_console(client, basic_user, user_password, login_path, console_path):
    response = client.post(
        login_path,
        data={"username": basic_user.username, "password": user_password},
        follow=False,
    )
    assert response.status_code == 302
    assert response["Location"] == console_path

    follow_response = client.get(console_path)
    assert follow_response.status_code == 200
    assert b"placeholder" in follow_response.content.lower()