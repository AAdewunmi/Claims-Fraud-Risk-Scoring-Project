# path: policylens/apps/claims/models.py
"""
Claims domain models.

Week 1 scope:
- Minimal workflow entities to support claim intake and an append-only audit trail.
- Fields are intentionally conservative to keep migrations stable early.
"""

from __future__ import annotations

from django.db import models


class PolicyHolder(models.Model):
    """A person or entity that owns a policy."""

    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name}".strip() or f"PolicyHolder:{self.pk}"