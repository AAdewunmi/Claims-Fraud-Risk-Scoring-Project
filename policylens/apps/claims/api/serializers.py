# path: policylens/apps/claims/api/serializers.py
"""
Serializers define the canonical API contract.

Week 1 implements the first contract for:
- POST /api/claims/
- GET /api/claims/?status=&priority=
"""

from __future__ import annotations

from rest_framework import serializers

from apps.claims import services
from apps.claims.models import Claim, Policy


class ClaimSerializer(serializers.ModelSerializer):
    """Serializer for claim list and create."""

    policy_id = serializers.PrimaryKeyRelatedField(
        source="policy",
        queryset=Policy.objects.all(),
        write_only=True,
    )
    policy_number = serializers.CharField(
        source="policy.policy_number",
        read_only=True)

    class Meta:
        model = Claim
        fields = [
            "id",
            "policy_id",
            "policy_number",
            "claim_type",
            "status",
            "priority",
            "summary",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_by",
            "created_at",
            "updated_at",
            "policy_number",
        ]

    def create(self, validated_data):
        """Create a claim via the domain service layer."""
        policy = validated_data.pop("policy")
        actor = str(self.context.get("actor") or "system")
        summary = validated_data.get("summary") or ""
        return services.create_claim(
            policy=policy,
            actor=actor,
            claim_type=validated_data["claim_type"],
            priority=validated_data["priority"],
            summary=summary,
        )
