# path: policylens/apps/claims/ml/scoring.py
"""
Scoring integration for the completeness classifier.

This service:
- Loads a versioned model bundle
- Validates contract metadata
- Extracts features from a claim
- Predicts probability of "incomplete"
- Produces score, label, and reason codes
- Persists MlScore
- Appends ML_SCORED audit evidence
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db import transaction

from apps.claims.ml.contracts import feature_contract_hash
from apps.claims.ml.features import extract_features
from apps.claims.ml.model_io import load_model_bundle, validate_meta_against_current_contract
from apps.claims.ml.reasons import reason_codes_from_features
from apps.claims.models import AuditEvent, Claim, MlScore


class ModelNotReady(Exception):
    """Raised when model artefacts are missing or invalid."""


@dataclass(frozen=True)
class ScoreResult:
    """Scoring output for a claim."""

    score: float
    label: str
    reason_codes: list[str]
    model_version: str
    threshold: float
    feature_contract_hash: str


def _label_for_score(*, score: float, threshold: float) -> str:
    """Return a deterministic label for a score and threshold."""
    return "LIKELY_INCOMPLETE" if score >= threshold else "LIKELY_COMPLETE"


def _append_ml_audit_event(*, claim: Claim, actor: str, result: ScoreResult) -> AuditEvent:
    """Append ML scoring evidence as an audit event."""
    return AuditEvent.objects.create(
        claim=claim,
        event_type="ML_SCORED",
        actor=actor,
        payload={
            "score": result.score,
            "label": result.label,
            "threshold": result.threshold,
            "reason_codes": result.reason_codes,
            "model_version": result.model_version,
            "feature_contract_hash": result.feature_contract_hash,
        },
    )


@transaction.atomic
def score_claim(*, claim: Claim, actor: str) -> MlScore:
    """Score a claim and persist MlScore + evidence.

    Raises:
        ModelNotReady: If model bundle cannot be loaded or validated.
    """
    model_version = getattr(settings, "ML_ACTIVE_MODEL_VERSION", "")
    threshold = float(getattr(settings, "ML_SCORE_THRESHOLD", 0.6))

    try:
        model, meta = load_model_bundle(model_version=model_version)
        validate_meta_against_current_contract(meta=meta)
    except Exception as exc:
        raise ModelNotReady(str(exc)) from exc

    features = extract_features(claim=claim)
    proba = float(model.predict_proba([features.values])[0][1])

    reasons = reason_codes_from_features(feature_dict=features.as_dict)
    label = _label_for_score(score=proba, threshold=threshold)
    contract_hash = feature_contract_hash()

    result = ScoreResult(
        score=proba,
        label=label,
        reason_codes=reasons,
        model_version=model_version,
        threshold=threshold,
        feature_contract_hash=contract_hash,
    )

    obj, _ = MlScore.objects.update_or_create(
        claim=claim,
        defaults={
            "score": result.score,
            "label": result.label,
            "reason_codes": result.reason_codes,
            "model_version": result.model_version,
            "threshold": result.threshold,
            "feature_contract_hash": result.feature_contract_hash,
        },
    )

    _append_ml_audit_event(claim=claim, actor=actor, result=result)
    return obj
