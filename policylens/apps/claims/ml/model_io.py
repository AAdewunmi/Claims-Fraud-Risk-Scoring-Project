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

from apps.claims.ml.contracts import FEATURE_CONTRACT_VERSION, FEATURE_NAMES, feature_contract_hash


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


def bundle_paths(*, model_version: str) -> tuple[Path, Path]:
    """Return (model_path, meta_path) for a given model version."""
    d = artifact_dir() / model_version
    d.mkdir(parents=True, exist_ok=True)
    return d / "model.joblib", d / "meta.json"


def save_model_bundle(*, model: Any, meta: ModelMeta) -> tuple[str, Path]:
    """Save model and meta to a versioned directory.

    Args:
        model: Any object supporting predict_proba(X).
        meta: ModelMeta.

    Returns:
        Tuple of (model_version, directory_path).
    """
    model_path, meta_path = bundle_paths(model_version=meta.model_version)
    joblib.dump(model, model_path)

    meta_path.write_text(json.dumps(meta.to_dict(), indent=2), encoding="utf-8")
    return meta.model_version, model_path.parent


def load_model_bundle(*, model_version: str) -> tuple[Any, ModelMeta]:
    """Load model and metadata by version.

    Raises:
        FileNotFoundError if artefacts do not exist.
    """
    model_path, meta_path = bundle_paths(model_version=model_version)
    if not model_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"Missing model bundle for version '{model_version}'.")

    model = joblib.load(model_path)
    meta = ModelMeta.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
    return model, meta


def validate_meta_against_current_contract(*, meta: ModelMeta) -> None:
    """Validate loaded metadata against the current feature contract."""
    current_hash = feature_contract_hash()
    if meta.feature_contract_version != FEATURE_CONTRACT_VERSION:
        raise ValueError("Feature contract version mismatch.")
    if meta.feature_contract_hash != current_hash:
        raise ValueError("Feature contract hash mismatch.")
    if meta.feature_names != list(FEATURE_NAMES):
        raise ValueError("Feature names ordering mismatch.")
