# path: policylens/apps/core/models.py
"""
Core models.

Sprint 3 adds an idempotency record model to support safe retries for write endpoints.
Sprint 7 adds admin governance models for operational settings, audit logs, and health checks.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class IdempotencyRecord(models.Model):
    """Persist idempotent responses for safe request retries.

    Uniqueness:
    - key + user + method + path

    request_hash exists to detect key reuse with different payload.
    """

    key = models.CharField(max_length=128)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="idempotency_records",
    )
    method = models.CharField(max_length=16)
    path = models.CharField(max_length=255)
    request_hash = models.CharField(max_length=64)

    response_status = models.PositiveIntegerField()
    response_body = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["key", "user", "method", "path"],
                name="uniq_idempotency_key_user_method_path",
            )
        ]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["key"]),
        ]

    def __str__(self) -> str:
        return f"IdempotencyRecord({self.key}, {self.method} {self.path})"


class AdminOperationalSetting(models.Model):
    """
    Admin-editable operational setting.

    The key/value pair is intentionally generic so the admin console can expose a
    controlled allow-list of settings without requiring schema changes per setting.
    """

    class ValueType(models.TextChoices):
        INTEGER = "INTEGER", "Integer"
        FLOAT = "FLOAT", "Float"
        BOOLEAN = "BOOLEAN", "Boolean"
        STRING = "STRING", "String"

    key = models.CharField(max_length=64, unique=True)
    value = models.CharField(max_length=255)
    value_type = models.CharField(max_length=16, choices=ValueType.choices)
    description = models.TextField(blank=True, default="")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_operational_settings_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.key}={self.value}"


class AdminAuditLog(models.Model):
    """Audit trail for admin console governance actions."""

    class EventType(models.TextChoices):
        USER_ROLE_UPDATED = "USER_ROLE_UPDATED", "User role updated"
        USER_ACCESS_UPDATED = "USER_ACCESS_UPDATED", "User access updated"
        CONFIG_UPDATED = "CONFIG_UPDATED", "Configuration updated"
        HEALTH_CHECKED = "HEALTH_CHECKED", "Health checked"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_audit_events",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_audit_target_events",
    )
    setting_key = models.CharField(max_length=64, blank=True, default="")
    message = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self) -> str:
        actor = getattr(self.actor, "username", "system")
        return f"{self.event_type} by {actor} at {self.created_at:%Y-%m-%d %H:%M:%S}"


class AdminHealthCheck(models.Model):
    """Snapshot of readiness checks initiated from the admin console."""

    status = models.CharField(max_length=16)
    details = models.JSONField(default=dict, blank=True)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_health_checks",
    )
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-checked_at"]
        indexes = [
            models.Index(fields=["status", "checked_at"]),
        ]

    def __str__(self) -> str:
        return f"HealthCheck(status={self.status}, checked_at={self.checked_at:%Y-%m-%d %H:%M:%S})"
