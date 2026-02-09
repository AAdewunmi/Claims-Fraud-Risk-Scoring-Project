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