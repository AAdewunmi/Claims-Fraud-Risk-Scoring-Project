"""
DB-hitting tests for console access behaviour.

Proof targets:
- anonymous console access redirects to the correct surface login entry point, with `next`
- authenticated wrong-role access returns 403 with the shared forbidden template
- allowed role access returns 200 and renders the expected console headings
- post-login redirect is deterministic by entry point
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user_password() -> str:
    return "pass-12345-strong"


@pytest.fixture()
def groups():
    """
    Create role groups used by console access checks.

    Group names are contracts, not implementation details.
    """
    return {
        "admin": Group.objects.create(name="admin"),
        "reviewer": Group.objects.create(name="reviewer"),
        "customer": Group.objects.create(name="customer"),
    }


@pytest.fixture()
def users(user_password, groups):
    """
    Create representative users for each role.

    Each user belongs to exactly one role group for clear boundary testing.
    """
    User = get_user_model()

    admin_user = User.objects.create_user(username="admin_user", password=user_password)
    admin_user.groups.add(groups["admin"])

    reviewer_user = User.objects.create_user(username="reviewer_user", password=user_password)
    reviewer_user.groups.add(groups["reviewer"])

    customer_user = User.objects.create_user(username="customer_user", password=user_password)
    customer_user.groups.add(groups["customer"])

    return {
        "admin": admin_user,
        "reviewer": reviewer_user,
        "customer": customer_user,
    }


@pytest.mark.parametrize(
    "console_path, expected_login_path",
    [
        ("/console/admin/", "/login/admin/"),
        ("/console/reviewer/", "/login/reviewer/"),
        ("/console/customer/", "/login/customer/"),
    ],
)
def test_console_anonymous_redirects_to_surface_login_with_next(
    client, console_path, expected_login_path
):
    response = client.get(console_path, follow=False)
    assert response.status_code == 302
    assert response["Location"] == f"{expected_login_path}?next={console_path}"


def test_admin_console_requires_admin_role(client, users, user_password):
    client.post(
        "/login/reviewer/", data={"username": users["reviewer"].username, "password": user_password}
    )
    response = client.get("/console/admin/")
    assert response.status_code == 403
    assert b"Forbidden" in response.content


def test_reviewer_console_requires_reviewer_or_admin(client, users, user_password):
    client.post(
        "/login/customer/", data={"username": users["customer"].username, "password": user_password}
    )
    response = client.get("/console/reviewer/")
    assert response.status_code == 403
    assert b"Forbidden" in response.content


def test_customer_console_requires_customer_or_admin(client, users, user_password):
    client.post(
        "/login/reviewer/", data={"username": users["reviewer"].username, "password": user_password}
    )
    response = client.get("/console/customer/")
    assert response.status_code == 403
    assert b"Forbidden" in response.content


def test_admin_console_renders_and_links_to_django_admin_and_other_consoles(
    client, users, user_password
):
    client.post(
        "/login/admin/", data={"username": users["admin"].username, "password": user_password}
    )
    response = client.get("/console/admin/")
    assert response.status_code == 200
    assert b"Admin console" in response.content
    assert b"/admin/" in response.content
    assert b"/console/reviewer/" in response.content
    assert b"/console/customer/" in response.content


@pytest.mark.parametrize(
    "role, console_path, heading",
    [
        ("reviewer", "/console/reviewer/", b"Reviewer console"),
        ("customer", "/console/customer/", b"Customer console"),
    ],
)
def test_role_console_renders_for_correct_role(
    client, users, user_password, role, console_path, heading
):
    client.post(
        f"/login/{role}/", data={"username": users[role].username, "password": user_password}
    )
    response = client.get(console_path)
    assert response.status_code == 200
    assert heading in response.content


@pytest.mark.parametrize(
    "login_path, expected_console_path",
    [
        ("/login/admin/", "/console/admin/"),
        ("/login/reviewer/", "/console/reviewer/"),
        ("/login/customer/", "/console/customer/"),
    ],
)
def test_post_login_redirect_is_deterministic_by_entry_point(
    client, users, user_password, login_path, expected_console_path
):
    # Pick the right role user for the login path.
    if login_path.endswith("/admin/"):
        user = users["admin"]
    elif login_path.endswith("/reviewer/"):
        user = users["reviewer"]
    else:
        user = users["customer"]

    response = client.post(
        login_path, data={"username": user.username, "password": user_password}, follow=False
    )
    assert response.status_code == 302
    assert response["Location"] == expected_console_path
