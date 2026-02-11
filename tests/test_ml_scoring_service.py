# path: policylens/tests/test_ml_scoring_service.py
"""
Integration test for ML scoring service.

This test writes a tiny fake model bundle to a temp directory and verifies:
- MlScore is persisted
- ML_SCORED audit evidence is appended
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import joblib
import pytest
from django.conf import settings
from django.utils import timezone

from apps.claims.ml.contracts import FEATURE_CONTRACT_VERSION, FEATURE_NAMES, feature_contract_hash
from apps.claims.ml.scoring import score_claim
from apps.claims.models import AuditEvent, Claim
from tests.factories import PolicyFactory


@dataclass
class FakeModel:
    """A minimal model with predict_proba matching sklearn shape."""

    fixed_proba: float

    def predict_proba(self, X):
        """Return [[p0, p1]] for each row."""
        p1 = float(self.fixed_proba)
        p0 = 1.0 - p1
        return [[p0, p1] for _ in X]


@pytest.mark.django_db
def test_score_claim_persists_mlscore_and_appends_audit_event(settings, tmp_path):
    """score_claim should create MlScore and ML_SCORED audit evidence."""
    # Write fake artefacts
    model_version = "test_v1"
    bundle_dir = tmp_path / "ml" / model_version
    bundle_dir.mkdir(parents=True, exist_ok=True)

    model_path = bundle_dir / "model.joblib"
    meta_path = bundle_dir / "meta.json"

    joblib.dump(FakeModel(fixed_proba=0.9), model_path)

    meta = {
        "model_version": model_version,
        "threshold": 0.6,
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "feature_contract_hash": feature_contract_hash(),
        "feature_names": list(FEATURE_NAMES),
        "metrics": {"accuracy": 1.0},
    }
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    settings.ML_ARTIFACT_DIR = str(tmp_path / "ml")
    settings.ML_ACTIVE_MODEL_VERSION = model_version
    settings.ML_SCORE_THRESHOLD = 0.6

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="A summary long enough to avoid SUMMARY_TOO_SHORT." + "x" * 50,
        created_by="tester",
        status=Claim.Status.NEW,
    )

    ml = score_claim(claim=claim, actor="tester")

    assert ml.claim_id == claim.id
    assert ml.score >= 0.9
    assert ml.label == "LIKELY_INCOMPLETE"
    assert ml.model_version == model_version
    assert ml.threshold == 0.6
    assert ml.feature_contract_hash == feature_contract_hash()

    event = AuditEvent.objects.filter(claim=claim, event_type="ML_SCORED").order_by("-created_at").first()
    assert event is not None
    assert event.payload["model_version"] == model_version
    assert event.payload["label"] == "LIKELY_INCOMPLETE"
