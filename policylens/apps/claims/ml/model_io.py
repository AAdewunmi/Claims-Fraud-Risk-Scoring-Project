# path: policylens/apps/claims/ml/model_io.py
"""
Model IO utilities for PolicyLens completeness classifier.

Artefacts:
- model.joblib
- meta.json

Meta enforces training–inference parity using:
- feature_contract_version
- feature_contract_hash
- feature_names (ordered)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
from django.conf import settings

from policylens.apps.claims.ml.contracts import FEATURE_CONTRACT_VERSION, FEATURE_NAMES, feature_contract_hash


@dataclass(frozen=True)
class ModelMeta:
    """Metadata describing a trained model artefact."""

    model_version: str
    threshold: float
    feature_contract_version: str
    feature_contract_hash: str
    feature_names: list[str]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialise metadata to a JSON-safe dict."""
        return {
            "model_version": self.model_version,
            "threshold": self.threshold,
            "feature_contract_version": self.feature_contract_version,
            "feature_contract_hash": self.feature_contract_hash,
            "feature_names": self.feature_names,
            "metrics": self.metrics,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ModelMeta":
        """Load ModelMeta from dict."""
        return ModelMeta(
            model_version=str(data["model_version"]),
            threshold=float(data["threshold"]),
            feature_contract_version=str(data["feature_contract_version"]),
            feature_contract_hash=str(data["feature_contract_hash"]),
            feature_names=list(data["feature_names"]),
            metrics=dict(data.get("metrics") or {}),
        )


def artifact_dir() -> Path:
    """Return the artefact directory for ML bundles."""
    base = getattr(settings, "ML_ARTIFACT_DIR", None)
    if base:
        return Path(base)
    return Path(settings.BASE_DIR).parent / "artifacts" / "ml"