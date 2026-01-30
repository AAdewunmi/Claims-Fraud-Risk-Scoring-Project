# path: policylens/apps/claims/api/serializers_audit.py
"""
Audit API serializers.

These are split out to keep audit contracts stable and reviewable.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.claims.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    """Read contract for audit events."""

    class Meta:
        model = AuditEvent
        fields = ["id", "event_type", "actor", "payload", "created_at"]
        read_only_fields = fields
