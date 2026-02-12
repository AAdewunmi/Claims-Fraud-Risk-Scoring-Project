# path: policylens/apps/claims/api/serializers_ml.py
"""
ML API serializers.

These serializers expose persisted MlScore objects.
"""

from __future__ import annotations

from rest_framework import serializers

from policylens.apps.claims.models import MlScore


class MlScoreSerializer(serializers.ModelSerializer):
    """Read contract for ML scores."""

    class Meta:
        model = MlScore
        fields = [
            "score",
            "label",
            "reason_codes",
            "model_version",
            "threshold",
            "feature_contract_hash",
            "scored_at",
        ]
        read_only_fields = fields
