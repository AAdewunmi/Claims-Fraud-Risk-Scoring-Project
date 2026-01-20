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
    
    
class Claim(models.Model):
    """A claim or policy change submission that moves through an ops review workflow."""

    class Type(models.TextChoices):
        CLAIM = "CLAIM", "Claim"
        POLICY_CHANGE = "POLICY_CHANGE", "Policy change"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        IN_REVIEW = "IN_REVIEW", "In review"
        DECIDED = "DECIDED", "Decided"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"

    policy = models.ForeignKey(Policy, on_delete=models.PROTECT, related_name="claims")
    claim_type = models.CharField(max_length=32, choices=Type.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.NORMAL)
    summary = models.TextField(blank=True)

    # Week 2 introduces roles and permissions. Week 1 keeps actor simple and string-based.
    created_by = models.CharField(max_length=128, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Claim:{self.pk} {self.status}"
    
    
class ClaimDocument(models.Model):
    """Document metadata linked to a claim.

    Week 1 stores metadata only. Week 2+ adds upload endpoints and storage integration.
    """

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="documents")
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=128, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    storage_key = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["claim", "uploaded_at"]),
        ]


class ChecklistItem(models.Model):
    """A deterministic checklist item used for completeness and review."""

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="checklist_items")
    key = models.CharField(max_length=64)
    label = models.CharField(max_length=255)
    is_required = models.BooleanField(default=True)
    is_satisfied = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("claim", "key")]
        indexes = [
            models.Index(fields=["claim", "is_satisfied"]),
        ]
        

class ReviewDecision(models.Model):
    """A decision record for a claim, forming the basis of a decision timeline."""

    class Decision(models.TextChoices):
        APPROVE = "APPROVE", "Approve"
        REJECT = "REJECT", "Reject"
        REQUEST_INFO = "REQUEST_INFO", "Request info"

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="decisions")
    decision = models.CharField(max_length=32, choices=Decision.choices)
    notes = models.TextField(blank=True)
    decided_by = models.CharField(max_length=128, blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["claim", "decided_at"]),
        ]