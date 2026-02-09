# path: policylens/apps/claims/ml/features.py
"""
Feature extraction for the completeness classifier.

This module converts a Claim instance into a numeric vector aligned to FEATURE_NAMES.
It must remain deterministic and side-effect free.
"""

from __future__ import annotations

from dataclasses import dataclass

from policylens.apps.claims.ml.contracts import FEATURE_NAMES
from policylens.apps.claims.models import ChecklistItem, Claim, ClaimDocument


@dataclass(frozen=True)
class FeatureResult:
    """Feature extraction output.

    Attributes:
        values: List of numeric values aligned to FEATURE_NAMES.
        as_dict: Dict keyed by FEATURE_NAMES for explanation and tests.
    """

    values: list[float]
    as_dict: dict[str, float]