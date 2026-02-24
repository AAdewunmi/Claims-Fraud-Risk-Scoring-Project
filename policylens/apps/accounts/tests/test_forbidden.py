"""
Tests for the forbidden surface endpoint.
"""

from django.urls import reverse


def test_forbidden_returns_403_and_renders_template(client):
    response = client.get(reverse("accounts:forbidden"))
    assert response.status_code == 403
    assert b"Forbidden" in response.content
    assert any(template.name == "site/forbidden.html" for template in response.templates)


def test_forbidden_rejects_non_get_methods(client):
    response = client.post(reverse("accounts:forbidden"))
    assert response.status_code == 405
