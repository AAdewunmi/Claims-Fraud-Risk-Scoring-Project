# path: policylens/apps/claims/ml/contracts.py
"""
Feature contract for the completeness classifier.

The contract is the source of truth for training and inference.
If FEATURE_NAMES order changes, the model is invalid.

Contract design principles:
- Stable ordering
- Numeric-only vector output
- Derived from claim fields and document metadata
"""

from __future__ import annotations

import hashlib
from typing import Final, Sequence

# Contract version should bump only when FEATURE_NAMES meaning or order changes.
FEATURE_CONTRACT_VERSION: Final[str] = "v1"

FEATURE_NAMES: Final[list[str]] = [
    # Claim core fields
    "claim_type_is_claim",
    "claim_type_is_policy_change",
    "priority_is_high",
    "priority_is_normal",
    "priority_is_low",
    "summary_length",
    "summary_has_digits",

    # Document metadata
    "documents_count",
    "documents_total_bytes",
    "documents_has_pdf",
    "documents_has_image",
    "documents_has_text",

    # Checklist completeness (if present)
    "checklist_required_count",
    "checklist_satisfied_count",
    "checklist_missing_required_count",
]


def feature_contract_hash(feature_names: Sequence[str] | None = None) -> str:
    """Return a sha256 hash of the feature contract.

    Args:
        feature_names: Optional override; defaults to FEATURE_NAMES.

    Returns:
        Hex digest used to detect training–inference drift.
    """
    names = list(feature_names or FEATURE_NAMES)
    payload = "|".join(names).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
