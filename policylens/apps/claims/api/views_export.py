# path: policylens/apps/claims/api/views_export.py
"""
Audit export API views.

This module serves the claim evidence bundle export.
The default format is JSON. Sprint 7 adds a PDF variant via `?format=pdf`.

Contracts
- GET /api/claims/{id}/audit-export/ returns JSON
- GET /api/claims/{id}/audit-export/?format=pdf returns PDF bytes
"""

from __future__ import annotations

from django.http import HttpResponse
from rest_framework import exceptions
from rest_framework.negotiation import (
    DefaultContentNegotiation,
    _MediaType,
    media_type_matches,
    order_by_precedence,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from policylens.apps.claims.export import build_audit_export, load_claim_for_export
from policylens.apps.claims.pdf_export import build_claim_audit_export_pdf


class _AuditExportContentNegotiation(DefaultContentNegotiation):
    """Disable DRF query-parameter format override for this endpoint."""

    def select_renderer(self, request, renderers, format_suffix=None):
        """Negotiate renderer without treating `?format=` as renderer selection."""
        fmt = format_suffix
        if fmt:
            renderers = self.filter_renderers(renderers, fmt)

        accepts = self.get_accept_list(request)
        for media_type_set in order_by_precedence(accepts):
            for renderer in renderers:
                for media_type in media_type_set:
                    if media_type_matches(renderer.media_type, media_type):
                        media_type_wrapper = _MediaType(media_type)
                        if (
                            _MediaType(renderer.media_type).precedence
                            > media_type_wrapper.precedence
                        ):
                            full_media_type = ";".join(
                                (renderer.media_type,)
                                + tuple(
                                    f"{key}={value}"
                                    for key, value in media_type_wrapper.params.items()
                                )
                            )
                            return renderer, full_media_type
                        return renderer, media_type

        raise exceptions.NotAcceptable(available_renderers=renderers)


class ClaimAuditExportAPIView(APIView):
    """
    Export a claim evidence bundle.

    The default export is JSON. PDF export can be requested with `?format=pdf`.
    """

    permission_classes = [IsAuthenticated]
    content_negotiation_class = _AuditExportContentNegotiation

    def get(self, request, claim_id: int):
        """
        Return deterministic export bundle as JSON or PDF.

        Args:
            request: Django request.
            claim_id: Claim primary key.

        Returns:
            DRF Response for JSON or Django HttpResponse for PDF.
        """
        claim = load_claim_for_export(claim_id=claim_id)
        payload = build_audit_export(claim=claim)

        export_format = (request.query_params.get("format") or "").strip().lower()

        if export_format == "pdf":
            pdf_bytes = build_claim_audit_export_pdf(payload=payload)
            resp = HttpResponse(pdf_bytes, content_type="application/pdf")
            resp["Content-Disposition"] = (
                f'attachment; filename="claim_{claim_id}_audit_export.pdf"'
            )
            return resp

        resp = Response(payload)
        resp["Content-Disposition"] = f'attachment; filename="claim_{claim_id}_audit_export.json"'
        return resp
