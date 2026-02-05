# path: policylens/apps/core/models.py
"""
Core models.

Week 3 adds an idempotency record model to support safe retries for write endpoints.
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="idempotency_records")
    method = models.CharField(max_length=16)
    path = models.CharField(max_length=255)
    request_hash = models.CharField(max_length=64)

    response_status = models.PositiveIntegerField()
    response_body = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["key", "user", "method", "path"], name="uniq_idempotency_key_user_method_path")
        ]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["key"]),
        ]

    def __str__(self) -> str:
        return f"IdempotencyRecord({self.key}, {self.method} {self.path})"
