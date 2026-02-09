# path: policylens/tests/test_ml_feature_contract.py
"""
Tests for the ML feature extraction contract.

These tests enforce training–inference parity by pinning feature order and values.
"""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from policylens.apps.claims.ml.contracts import FEATURE_NAMES, feature_contract_hash
from policylens.apps.claims.ml.features import extract_features
from policylens.apps.claims.models import Claim, ClaimDocument, ChecklistItem
from tests.factories import PolicyFactory


@pytest.mark.django_db
def test_feature_contract_hash_is_stable_for_v1():
    """Contract hash should not change unless FEATURE_NAMES meaning or order changes."""
    h1 = feature_contract_hash()
    h2 = feature_contract_hash()
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.django_db
def test_extract_features_returns_values_aligned_to_feature_names(settings, tmp_path):
    """Feature vector must align with FEATURE_NAMES ordering."""
    settings.MEDIA_ROOT = tmp_path

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        status=Claim.Status.NEW,
        priority=Claim.Priority.HIGH,
        summary="Short summary 123",
        created_by="tester",
    )

    ChecklistItem.objects.create(claim=claim, key="id", label="ID", is_required=True, is_satisfied=False)
    ChecklistItem.objects.create(claim=claim, key="addr", label="Address", is_required=True, is_satisfied=True)

    uploaded = SimpleUploadedFile("doc.pdf", b"pdfdata", content_type="application/pdf")
    ClaimDocument.objects.create(
        claim=claim,
        file=uploaded,
        original_filename="doc.pdf",
        content_type="application/pdf",
        size_bytes=7,
        uploaded_by="tester",
    )

    result = extract_features(claim=claim)
    assert len(result.values) == len(FEATURE_NAMES)

    d = result.as_dict
    assert d["priority_is_high"] == 1.0
    assert d["priority_is_low"] == 0.0
    assert d["summary_has_digits"] == 1.0
    assert d["documents_count"] == 1.0
    assert d["documents_has_pdf"] == 1.0
    assert d["checklist_required_count"] == 2.0
    assert d["checklist_satisfied_count"] == 1.0
    assert d["checklist_missing_required_count"] == 1.0

    # Spot check ordering: the vector should match dict values by FEATURE_NAMES sequence.
    for idx, name in enumerate(FEATURE_NAMES):
        assert result.values[idx] == float(d[name])
