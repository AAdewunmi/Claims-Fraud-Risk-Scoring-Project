# path: tests/test_audit_export_pdf.py
"""
Integration test for PDF audit export output.

This proves the PDF export path:
- returns 200 for an authenticated caller
- returns a PDF content type
- returns bytes beginning with %PDF
- includes an attachment filename with .pdf
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from policylens.apps.claims.models import Claim
from tests.factories import PolicyFactory

User = get_user_model()


@pytest.mark.django_db
def test_audit_export_pdf_is_generated_and_returned(api_client):
    """
    The PDF export should be generated deterministically and returned as bytes.

    This test focuses on the boundary contract, not PDF content parsing.
    """
    user = User.objects.create_user(username="export_pdf_user", password="password123")
    api_client.force_authenticate(user=user)

    policy = PolicyFactory()

    create_url = reverse("claims-list-create")
    claim_resp = api_client.post(
        create_url,
        data={
            "policy_id": policy.pk,
            "claim_type": Claim.Type.CLAIM,
            "priority": Claim.Priority.NORMAL,
            "summary": "PDF export test",
        },
        format="json",
    )
    assert claim_resp.status_code == 201
    claim_id = claim_resp.json()["id"]

    doc_url = reverse("claims-documents-create", kwargs={"claim_id": claim_id})
    uploaded = SimpleUploadedFile("evidence.txt", b"hello", content_type="text/plain")
    doc_resp = api_client.post(
        doc_url,
        data={
            "file": uploaded,
            "original_filename": "evidence.txt",
            "content_type": "text/plain",
        },
        format="multipart",
    )
    assert doc_resp.status_code == 201

    export_url = reverse("claims-audit-export", kwargs={"claim_id": claim_id})
    export_resp = api_client.get(f"{export_url}?format=pdf")

    assert export_resp.status_code == 200
    assert export_resp["Content-Type"].startswith("application/pdf")

    content_disposition = export_resp.get("Content-Disposition", "")
    assert "attachment" in content_disposition
    assert content_disposition.endswith(f'claim_{claim_id}_audit_export.pdf"')

    body = export_resp.content
    assert body[:4] == b"%PDF"
    assert len(body) > 300
