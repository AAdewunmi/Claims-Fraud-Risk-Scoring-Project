# path: policylens/apps/claims/api/serializers.py
"""
Serializers define the canonical API contract.

Sprint 4 surfaces ml_score fields in claim detail.
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

ALLOWED_DOCUMENT_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png", "text/plain"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


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
    """Claim detail contract used by ops screens later."""

    policy_number = serializers.CharField(source="policy.policy_number", read_only=True)
    documents_count = serializers.IntegerField(read_only=True)
    notes_count = serializers.IntegerField(read_only=True)
    decisions_count = serializers.IntegerField(read_only=True)
    ml_score = serializers.SerializerMethodField()

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
            "ml_score",
        ]

    def get_ml_score(self, obj: Claim):
        """Return persisted ml_score fields if available."""
        ml = getattr(obj, "ml_score", None)
        if ml is None:
            return None
        return {
            "score": ml.score,
            "label": ml.label,
            "reason_codes": ml.reason_codes,
            "model_version": ml.model_version,
            "threshold": ml.threshold,
            "feature_contract_hash": ml.feature_contract_hash,
            "scored_at": ml.scored_at.isoformat(),
        }


class ClaimDocumentUploadSerializer(serializers.Serializer):
    """Contract for uploading a document to a claim."""

    file = serializers.FileField()
    original_filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=128, required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate size and content type deterministically."""
        uploaded_file = attrs["file"]
        size_bytes = getattr(uploaded_file, "size", 0) or 0
        if size_bytes <= 0:
            raise serializers.ValidationError({"file": "Uploaded file is empty."})
        if size_bytes > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError(
                {"file": f"File exceeds max size of {MAX_UPLOAD_BYTES} bytes."}
            )

        content_type = attrs.get("content_type") or getattr(uploaded_file, "content_type", "") or ""
        if content_type and content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
            raise serializers.ValidationError({"content_type": "Unsupported content type."})

        return attrs

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

    def validate_body(self, value: str) -> str:
        """Ensure note body is non-empty and trimmed."""
        if not value or not value.strip():
            raise serializers.ValidationError("Note body is required.")
        return value.strip()

    def create(self, validated_data):
        """Create note via domain service."""
        claim: Claim = self.context["claim"]
        actor = str(self.context.get("actor") or "system")
        return services.add_note(claim=claim, body=validated_data["body"], actor=actor)


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
