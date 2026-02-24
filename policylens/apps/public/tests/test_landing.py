"""
Tests for public landing page routing and surface links.
"""

import re

import pytest
from django.urls import Resolver404, resolve, reverse


def test_landing_page_renders_expected_template(client):
    response = client.get(reverse("public:landing"))
    assert response.status_code == 200
    assert b"PolicyLens" in response.content
    rendered_templates = {template.name for template in response.templates if template.name}
    assert "public/landing.html" in rendered_templates


@pytest.mark.parametrize("role_label", ["Admin", "Reviewer", "Customer"])
def test_landing_role_links_exist_and_resolve(client, role_label):
    response = client.get(reverse("public:landing"))
    html = response.content.decode("utf-8")
    pattern = rf'<a[^>]+href="(?P<href>[^"]+)"[^>]*>\s*{role_label}\s*</a>'
    match = re.search(pattern, html)
    assert match is not None, f"Missing {role_label} link on landing page."

    target = match.group("href")
    try:
        resolve(target)
    except Resolver404 as exc:
        raise AssertionError(f"{role_label} link points to unresolved route: {target}") from exc
