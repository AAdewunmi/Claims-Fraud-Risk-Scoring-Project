# path: policylens/apps/claims/management/commands/train_completeness_model.py
"""
Train the completeness classifier and save a versioned model bundle.

This command:
- Reads a synthetic dataset CSV (or any CSV matching the contract)
- Trains a lightweight model
- Saves artefacts to artifacts/ml/<version>/
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from policylens.apps.claims.ml.train import train_from_csv


class Command(BaseCommand):
    """Train the completeness model."""

    help = "Train completeness classifier from a contract-aligned CSV dataset."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--csv", required=True, help="Input dataset path.")
        parser.add_argument(
            "--model-version", required=True, help="Model version folder name, e.g. v1_2026_01_13."
        )
        parser.add_argument(
            "--threshold", type=float, default=0.6, help="Threshold for likely incomplete."
        )
        parser.add_argument("--seed", type=int, default=42, help="Deterministic training seed.")

    def handle(self, *args, **options) -> None:
        csv_path = Path(options["csv"])
        version = str(options["model_version"])
        threshold = float(options["threshold"])
        seed = int(options["seed"])

        result = train_from_csv(
            csv_path=csv_path, model_version=version, threshold=threshold, random_seed=seed
        )
        self.stdout.write(self.style.SUCCESS(f"Trained model {result.model_version}"))
        self.stdout.write(self.style.SUCCESS(f"Metrics: {result.metrics}"))
