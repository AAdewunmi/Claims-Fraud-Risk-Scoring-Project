# path: policylens/apps/claims/api/views_export.py
"""Audit export API views."""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from policylens.apps.claims.export import build_audit_export, load_claim_for_export


class ClaimAuditExportAPIView(APIView):
    """Export a claim evidence bundle.

    Contract:
    - GET /api/claims/{id}/audit-export/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id: int):
        """Return deterministic export bundle as JSON."""
        claim = load_claim_for_export(claim_id=claim_id)
        payload = build_audit_export(claim=claim)

        resp = Response(payload)
        resp["Content-Disposition"] = f'attachment; filename="claim_{claim_id}_audit_export.json"'
        return resp
