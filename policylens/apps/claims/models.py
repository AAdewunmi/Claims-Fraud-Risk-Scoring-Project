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
    
    
class Policy(models.Model):
    """An insurance policy linked to a policy holder."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        LAPSED = "LAPSED", "Lapsed"
        CANCELLED = "CANCELLED", "Cancelled"

    holder = models.ForeignKey(PolicyHolder, on_delete=models.PROTECT, related_name="policies")
    policy_number = models.CharField(max_length=64, unique=True)
    product_type = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["policy_number"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return self.policy_number