# path: policylens/tests/test_audit_export_includes_ml.py
"""
Integration test: audit export includes ml_score after scoring.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import joblib
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from policylens.apps.claims.ml.contracts import (
    FEATURE_CONTRACT_VERSION,
    FEATURE_NAMES,
    feature_contract_hash,
)
from policylens.apps.claims.models import Claim

User = get_user_model()


@dataclass
class FakeModel:
    """Minimal predict_proba model for export tests."""

    fixed_proba: float

    def predict_proba(self, X):
        p1 = float(self.fixed_proba)
        p0 = 1.0 - p1
        return [[p0, p1] for _ in X]


@pytest.mark.django_db
def test_audit_export_includes_ml_score_after_scoring(api_client, settings, tmp_path):
    """Export should include ml_score when present."""
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    reviewer = User.objects.create_user(
        username="export_ml_reviewer",
        password="password123",
    )
    reviewer.groups.add(reviewer_group)
    api_client.force_authenticate(user=reviewer)

    # Prepare fake model artefacts
    model_version = "export_test_v1"
    bundle_dir = tmp_path / "ml" / model_version
    bundle_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(FakeModel(fixed_proba=0.8), bundle_dir / "model.joblib")
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

    # Create a claim via API so it has SLA evidence in your workflow
    from tests.factories import PolicyFactory

    policy = PolicyFactory()
    create_url = reverse("claims-list-create")
    c = api_client.post(
        create_url,
        data={
            "policy_id": policy.pk,
            "claim_type": Claim.Type.CLAIM,
            "priority": Claim.Priority.NORMAL,
            "summary": "Export ML test " + "x" * 80,
        },
        format="json",
    )
    assert c.status_code == 201
    claim_id = c.json()["id"]

    # Score it
    score_url = reverse("claims-ml-score", kwargs={"claim_id": claim_id})
    s = api_client.post(score_url)
    assert s.status_code == 200

    # Export it
    export_url = reverse("claims-audit-export", kwargs={"claim_id": claim_id})
    e = api_client.get(export_url)
    assert e.status_code == 200

    payload = e.json()
    assert payload["ml_score"] is not None
    assert payload["ml_score"]["model_version"] == model_version
    assert payload["ml_score"]["feature_contract_hash"] == feature_contract_hash()
