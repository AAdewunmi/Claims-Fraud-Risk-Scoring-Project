# path: policylens/apps/claims/api/serializers.py
"""
Serializers define the canonical API contract.

Week 2 adds nested contracts for:
- GET /api/claims/{id}/
- POST /api/claims/{id}/documents/
- POST /api/claims/{id}/notes/
- POST /api/claims/{id}/decisions/
"""

from __future__ import annotations

from rest_framework import serializers

from policylens.apps.claims import services
from policylens.apps.claims.models import (
    Claim,
    ClaimDocument,
    InternalNote,
    Policy,
    ReviewDecision,
)


class ClaimSerializer(serializers.ModelSerializer):
    """Serializer for claim list and create."""

    policy_id = serializers.PrimaryKeyRelatedField(
        source="policy",
        queryset=Policy.objects.all(),
        write_only=True,
    )
    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)

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


class ClaimDetailSerializer(serializers.ModelSerializer):
    """Claim detail contract used by ops screens later.

    Keep it stable and intentionally small in week 2.
    """

    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)
    documents_count = serializers.IntegerField(read_only=True)
    notes_count = serializers.IntegerField(read_only=True)
    decisions_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Claim
        fields = [
            "id",
            "policy_number",
            "claim_type",
            "status",
            "priority",
            "summary",
            "created_by",
            "created_at",
            "updated_at",
            "documents_count",
            "notes_count",
            "decisions_count",
        ]


class ClaimDocumentUploadSerializer(serializers.Serializer):
    """Contract for uploading a document to a claim."""

    file = serializers.FileField()
    original_filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=128, required=False, allow_blank=True)

    def create(self, validated_data):
        """Create document via domain service."""
        claim: Claim = self.context["claim"]
        actor = str(self.context.get("actor") or "system")
        uploaded_file = validated_data["file"]
        original_filename = validated_data["original_filename"]
        content_type = (
            validated_data.get("content_type") or getattr(uploaded_file, "content_type", "") or ""
        )

        return services.add_document(
            claim=claim,
            uploaded_file=uploaded_file,
            original_filename=original_filename,
            content_type=content_type,
            actor=actor,
        )


class ClaimDocumentSerializer(serializers.ModelSerializer):
    """Read contract for uploaded claim documents."""

    class Meta:
        model = ClaimDocument
        fields = [
            "id",
            "original_filename",
            "content_type",
            "size_bytes",
            "uploaded_by",
            "uploaded_at",
            "file",
        ]
        read_only_fields = fields


class InternalNoteCreateSerializer(serializers.Serializer):
    """Contract for creating an internal note on a claim."""

    body = serializers.CharField()

    def create(self, validated_data):
        """Create note via domain service."""
        claim: Claim = self.context["claim"]
        actor = str(self.context.get("actor") or "system")
        return services.add_note(
            claim=claim,
            body=validated_data["body"],
            actor=actor,
        )


class InternalNoteSerializer(serializers.ModelSerializer):
    """Read contract for internal notes."""

    class Meta:
        model = InternalNote
        fields = ["id", "body", "created_by", "created_at"]
        read_only_fields = fields


class ReviewDecisionCreateSerializer(serializers.Serializer):
    """Contract for recording a decision for a claim."""

    decision = serializers.ChoiceField(choices=ReviewDecision.Decision.choices)
    notes = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        """Create decision via domain service."""
        claim: Claim = self.context["claim"]
        actor = str(self.context.get("actor") or "system")
        return services.add_decision(
            claim=claim,
            decision=validated_data["decision"],
            notes=validated_data.get("notes") or "",
            actor=actor,
        )


class ReviewDecisionSerializer(serializers.ModelSerializer):
    """Read contract for decisions."""

    class Meta:
        model = ReviewDecision
        fields = ["id", "decision", "notes", "decided_by", "decided_at"]
        read_only_fields = fields
