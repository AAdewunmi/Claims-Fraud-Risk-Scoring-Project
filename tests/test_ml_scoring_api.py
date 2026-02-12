# path: policylens/tests/test_ml_scoring_api.py
"""
Integration tests for ML scoring API endpoint.

This test uses a fake model bundle to avoid depending on long training runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import joblib
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from policylens.apps.claims.ml.contracts import FEATURE_CONTRACT_VERSION, FEATURE_NAMES, feature_contract_hash
from policylens.apps.claims.models import Claim
from tests.factories import PolicyFactory

User = get_user_model()


@dataclass
class FakeModel:
    """Minimal predict_proba model for endpoint tests."""

    fixed_proba: float

    def predict_proba(self, X):
        p1 = float(self.fixed_proba)
        p0 = 1.0 - p1
        return [[p0, p1] for _ in X]


@pytest.mark.django_db
def test_ml_score_endpoint_returns_contract(api_client, settings, tmp_path):
    """POST /ml-score should return ML contract and persist score."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    reviewer = User.objects.create_user(username="ml_reviewer", password="password123")
    reviewer.groups.add(reviewer_group)
    api_client.force_authenticate(user=reviewer)

    model_version = "api_test_v1"
    bundle_dir = tmp_path / "ml" / model_version
    bundle_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(FakeModel(fixed_proba=0.75), bundle_dir / "model.joblib")
    (bundle_dir / "meta.json").write_text(
        json.dumps(
            {
                "model_version": model_version,
                "threshold": 0.6,
                "feature_contract_version": FEATURE_CONTRACT_VERSION,
                "feature_contract_hash": feature_contract_hash(),
                "feature_names": list(FEATURE_NAMES),
                "metrics": {"accuracy": 1.0},
            }
        ),
        encoding="utf-8",
    )

    settings.ML_ARTIFACT_DIR = str(tmp_path / "ml")
    settings.ML_ACTIVE_MODEL_VERSION = model_version
    settings.ML_SCORE_THRESHOLD = 0.6

    policy = PolicyFactory()
    claim = Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        priority=Claim.Priority.NORMAL,
        summary="This summary is long enough to avoid SUMMARY_TOO_SHORT." + "x" * 60,
        created_by="seed",
        status=Claim.Status.NEW,
    )

    url = reverse("claims-ml-score", kwargs={"claim_id": claim.id})
    resp = api_client.post(url)
    assert resp.status_code == 200

    body = resp.json()
    assert "score" in body
    assert body["label"] in {"LIKELY_INCOMPLETE", "LIKELY_COMPLETE"}
    assert isinstance(body["reason_codes"], list)
    assert body["model_version"] == model_version
    assert body["threshold"] == 0.6
    assert body["feature_contract_hash"] == feature_contract_hash()
