"""
Public landing page contract tests.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


def test_landing_uses_header_role_navigation_instead_of_role_buttons(client):
    response = client.get("/")
    assert response.status_code == 200

    content = response.content
    assert b'<a class="nav-link" href="/login/admin/">Admin</a>' in content
    assert b'<a class="nav-link" href="/login/reviewer/">Reviewer</a>' in content
    assert b'<a class="nav-link" href="/login/customer/">Customer</a>' in content

    assert b'<a class="button" href="/login/admin/">Admin</a>' not in content
    assert b'<a class="button" href="/login/reviewer/">Reviewer</a>' not in content
    assert b'<a class="button button-secondary" href="/login/customer/">Customer</a>' not in content
