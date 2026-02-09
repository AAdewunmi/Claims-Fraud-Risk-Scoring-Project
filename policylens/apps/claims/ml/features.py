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


def _bool(value: bool) -> float:
    """Convert bool to float for model compatibility."""
    return 1.0 if value else 0.0


def extract_features(*, claim: Claim) -> FeatureResult:
    """Extract deterministic features for a claim.

    Args:
        claim: Claim instance. Related fields may be queried.

    Returns:
        FeatureResult containing vector and dict aligned to FEATURE_NAMES.
    """
    claim_type_is_claim = claim.claim_type == Claim.Type.CLAIM
    claim_type_is_policy_change = claim.claim_type == Claim.Type.POLICY_CHANGE

    priority_is_high = claim.priority == Claim.Priority.HIGH
    priority_is_normal = claim.priority == Claim.Priority.NORMAL
    priority_is_low = claim.priority == Claim.Priority.LOW

    summary = claim.summary or ""
    summary_length = float(len(summary))
    summary_has_digits = any(ch.isdigit() for ch in summary)

    docs = ClaimDocument.objects.filter(claim=claim)
    documents_count = float(docs.count())
    documents_total_bytes = float(sum((d.size_bytes or 0) for d in docs))
    documents_has_pdf = any((d.content_type or "").lower() == "application/pdf" for d in docs)
    documents_has_image = any(
        (d.content_type or "").lower() in {"image/jpeg", "image/png"} for d in docs
    )
    documents_has_text = any((d.content_type or "").lower() == "text/plain" for d in docs)

    checklist = ChecklistItem.objects.filter(claim=claim)
    required_count = float(checklist.filter(is_required=True).count())
    satisfied_count = float(checklist.filter(is_required=True, is_satisfied=True).count())
    missing_required_count = float(max(int(required_count - satisfied_count), 0))

    features: dict[str, float] = {
        "claim_type_is_claim": _bool(claim_type_is_claim),
        "claim_type_is_policy_change": _bool(claim_type_is_policy_change),
        "priority_is_high": _bool(priority_is_high),
        "priority_is_normal": _bool(priority_is_normal),
        "priority_is_low": _bool(priority_is_low),
        "summary_length": summary_length,
        "summary_has_digits": _bool(summary_has_digits),
        "documents_count": documents_count,
        "documents_total_bytes": documents_total_bytes,
        "documents_has_pdf": _bool(documents_has_pdf),
        "documents_has_image": _bool(documents_has_image),
        "documents_has_text": _bool(documents_has_text),
        "checklist_required_count": required_count,
        "checklist_satisfied_count": satisfied_count,
        "checklist_missing_required_count": missing_required_count,
    }

    # Align values to the contract ordering.
    values = [float(features[name]) for name in FEATURE_NAMES]
    return FeatureResult(values=values, as_dict=features)
