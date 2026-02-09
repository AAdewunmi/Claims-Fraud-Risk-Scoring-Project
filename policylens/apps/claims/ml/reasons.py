# path: policylens/apps/claims/ml/reasons.py
"""
Deterministic reason codes for "likely incomplete" flags.

Reason codes must be:
- Stable (same inputs -> same outputs)
- Ordered (a fixed ordering for display and tests)
- Human-readable enough for ops workflows
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ReasonRule:
    """A rule producing a reason code based on extracted features."""

    code: str
    predicate: callable


# Thresholds are part of behaviour and should be treated as product configuration.
SUMMARY_MIN_LENGTH: Final[int] = 40
DOCS_MIN_COUNT: Final[int] = 1


REASON_RULES: Final[list[ReasonRule]] = [
    ReasonRule(
        code="NO_DOCUMENTS",
        predicate=lambda f: f.get("documents_count", 0) < DOCS_MIN_COUNT,
    ),
    ReasonRule(
        code="SUMMARY_TOO_SHORT",
        predicate=lambda f: f.get("summary_length", 0) < SUMMARY_MIN_LENGTH,
    ),
    ReasonRule(
        code="MISSING_REQUIRED_CHECKLIST_ITEMS",
        predicate=lambda f: f.get("checklist_missing_required_count", 0) > 0,
    ),
    ReasonRule(
        code="NO_MACHINE_READABLE_DOCS",
        predicate=lambda f: (f.get("documents_has_pdf", 0) + f.get("documents_has_text", 0)) == 0
        and f.get("documents_count", 0) >= DOCS_MIN_COUNT,
    ),
]


def reason_codes_from_features(*, feature_dict: dict[str, float]) -> list[str]:
    """Return deterministic reason codes derived from features.

    Args:
        feature_dict: Feature dict keyed by feature names.

    Returns:
        List of reason codes in stable order.
    """
    codes: list[str] = []
    for rule in REASON_RULES:
        if rule.predicate(feature_dict):
            codes.append(rule.code)
    return codes
