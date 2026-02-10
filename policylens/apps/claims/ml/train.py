# path: policylens/apps/claims/ml/train.py
"""
Training logic for the completeness classifier.

This module is intentionally small. It trains on a CSV with FEATURE_NAMES columns.

Data contract:
- Each feature column exists in FEATURE_NAMES order
- is_incomplete column exists with values 0/1
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

from policylens.apps.claims.ml.contracts import FEATURE_CONTRACT_VERSION, FEATURE_NAMES, feature_contract_hash
from policylens.apps.claims.ml.model_io import ModelMeta, save_model_bundle


@dataclass(frozen=True)
class TrainResult:
    """Training result summary."""

    model_version: str
    threshold: float
    metrics: dict


def _read_csv(*, path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read CSV into X, y arrays using FEATURE_NAMES as columns."""
    rows: list[list[float]] = []
    labels: list[int] = []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        expected = set(FEATURE_NAMES + ["is_incomplete"])
        if set(reader.fieldnames or []) != expected:
            raise ValueError("CSV columns must match FEATURE_NAMES plus is_incomplete label.")
        for r in reader:
            rows.append([float(r[name]) for name in FEATURE_NAMES])
            labels.append(int(r["is_incomplete"]))

    return np.asarray(rows, dtype=float), np.asarray(labels, dtype=int)


def train_from_csv(*, csv_path: Path, model_version: str, threshold: float, random_seed: int = 42) -> TrainResult:
    """Train logistic regression and save a model bundle.

    Args:
        csv_path: Path to dataset CSV.
        model_version: Directory name for saved artefacts.
        threshold: Probability threshold for "likely incomplete".
        random_seed: Deterministic training seed.

    Returns:
        TrainResult.
    """
    X, y = _read_csv(path=csv_path)

    model = LogisticRegression(
        random_state=random_seed,
        max_iter=500,
        solver="lbfgs",
    )
    model.fit(X, y)

    preds = (model.predict_proba(X)[:, 1] >= threshold).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(y, preds)),
        "n_rows": int(X.shape[0]),
        "random_seed": int(random_seed),
    }

    meta = ModelMeta(
        model_version=model_version,
        threshold=float(threshold),
        feature_contract_version=FEATURE_CONTRACT_VERSION,
        feature_contract_hash=feature_contract_hash(),
        feature_names=list(FEATURE_NAMES),
        metrics=metrics,
    )

    save_model_bundle(model=model, meta=meta)
    return TrainResult(model_version=model_version, threshold=float(threshold), metrics=metrics)
