# path: tests/test_audit_export_negotiation.py
"""Unit tests for audit export content negotiation behavior."""

from __future__ import annotations

import pytest
from rest_framework import exceptions
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIRequestFactory

from policylens.apps.claims.api.views_export import _AuditExportContentNegotiation


def test_select_renderer_with_format_suffix_filters_renderer() -> None:
    """Format suffix should filter renderers without relying on query param format override."""
    factory = APIRequestFactory()
    request = factory.get("/api/claims/1/audit-export/")
    negotiation = _AuditExportContentNegotiation()

    renderer, media_type = negotiation.select_renderer(
        request=request,
        renderers=[JSONRenderer()],
        format_suffix="json",
    )

    assert renderer.format == "json"
    assert media_type == "application/json"


def test_select_renderer_preserves_specific_accept_media_type() -> None:
    """Specific Accept header media types should be returned unchanged."""
    factory = APIRequestFactory()
    request = factory.get(
        "/api/claims/1/audit-export/",
        HTTP_ACCEPT="application/json; indent=8",
    )
    negotiation = _AuditExportContentNegotiation()

    _, media_type = negotiation.select_renderer(
        request=request,
        renderers=[JSONRenderer()],
        format_suffix=None,
    )

    assert media_type == "application/json; indent=8"


def test_select_renderer_raises_not_acceptable_for_unsupported_accept() -> None:
    """Unsupported Accept headers should raise DRF NotAcceptable."""
    factory = APIRequestFactory()
    request = factory.get("/api/claims/1/audit-export/", HTTP_ACCEPT="application/xml")
    negotiation = _AuditExportContentNegotiation()

    with pytest.raises(exceptions.NotAcceptable):
        negotiation.select_renderer(
            request=request,
            renderers=[JSONRenderer()],
            format_suffix=None,
        )
