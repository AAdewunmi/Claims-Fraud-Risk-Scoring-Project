# path: policylens/tests/test_ml_reason_codes.py
"""
Tests for deterministic reason code generation.
"""

from __future__ import annotations

from policylens.apps.claims.ml.reasons import reason_codes_from_features


def test_reason_codes_are_stable_and_ordered_for_known_inputs():
    """Reason code list must be deterministic and ordered."""
    features = {
        "documents_count": 0.0,
        "summary_length": 10.0,
        "checklist_missing_required_count": 1.0,
        "documents_has_pdf": 0.0,
        "documents_has_text": 0.0,
    }

    codes = reason_codes_from_features(feature_dict=features)
    assert codes == [
        "NO_DOCUMENTS",
        "SUMMARY_TOO_SHORT",
        "MISSING_REQUIRED_CHECKLIST_ITEMS",
    ]
