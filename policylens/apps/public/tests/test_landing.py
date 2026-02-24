"""
Tests for public landing page routing and surface links.
"""

import re

import pytest
from django.urls import resolve, reverse


def test_landing_page_renders_expected_template(client):
    response = client.get(reverse("public:landing"))
    assert response.status_code == 200
    assert b"PolicyLens" in response.content
    rendered_templates = {template.name for template in response.templates if template.name}
    assert "public/landing.html" in rendered_templates


def _extract_role_href(html, role_label):
    pattern = rf'<a[^>]+href="(?P<href>[^"]+)"[^>]*>\s*{role_label}\s*</a>'
    match = re.search(pattern, html)
    assert match is not None, f"Missing {role_label} link on landing page."
    return match.group("href")


@pytest.mark.parametrize("role_label", ["Admin", "Reviewer", "Customer"])
def test_landing_role_links_exist(client, role_label):
    response = client.get(reverse("public:landing"))
    html = response.content.decode("utf-8")
    _extract_role_href(html, role_label)


@pytest.mark.parametrize("role_label", ["Admin", "Reviewer", "Customer"])
def test_landing_role_links_resolve(client, role_label):
    response = client.get(reverse("public:landing"))
    html = response.content.decode("utf-8")
    target = _extract_role_href(html, role_label)
    resolve(target)
