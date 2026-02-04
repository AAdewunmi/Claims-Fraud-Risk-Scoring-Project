"""
Audit export builder.

Export must be deterministic:
- Stable keys
- Chronological ordering for timeline-like sections
- No file contents, only metadata and URLs
"""

from __future__ import annotations

from django.db.models import Prefetch
from django.utils import timezone

from policylens.apps.claims.models import (
    AuditEvent,
    Claim,
    ClaimDocument,
    InternalNote,
    ReviewDecision,
)


def build_audit_export(*, claim: Claim) -> dict:
    """Build an evidence-grade export bundle for a claim.

    Args:
        claim: Claim instance (may be unfetched). Caller should pass a fully loaded claim.

    Returns:
        Dict suitable for JSON response and persistence.
    """
    policy = claim.policy
    holder = policy.holder

    documents = list(claim.documents.all().order_by("uploaded_at"))
    notes = list(claim.notes.all().order_by("created_at"))
    decisions = list(claim.decisions.all().order_by("decided_at"))
    audit_events = list(claim.audit_events.all().order_by("created_at"))

    sla_clock = getattr(claim, "sla_clock", None)

    return {
        "export_version": "v1",
        "exported_at": timezone.now().isoformat(),
        "claim": {
            "id": claim.pk,
            "claim_type": claim.claim_type,
            "status": claim.status,
            "priority": claim.priority,
            "summary": claim.summary,
            "created_by": claim.created_by,
            "created_at": claim.created_at.isoformat(),
            "updated_at": claim.updated_at.isoformat(),
        },
        "policy": {
            "id": policy.pk,
            "policy_number": policy.policy_number,
            "product_type": policy.product_type,
            "status": policy.status,
            "effective_date": policy.effective_date.isoformat() if policy.effective_date else None,
            "expiry_date": policy.expiry_date.isoformat() if policy.expiry_date else None,
        },
        "policy_holder": {
            "id": holder.pk,
            "full_name": holder.full_name,
            "email": holder.email,
            "phone": holder.phone,
        },
        "sla_clock": (
            None
            if sla_clock is None
            else {
                "started_at": sla_clock.started_at.isoformat(),
                "due_at": sla_clock.due_at.isoformat() if sla_clock.due_at else None,
                "breached_at": sla_clock.breached_at.isoformat() if sla_clock.breached_at else None,
            }
        ),
        "documents": [
            {
                "id": d.pk,
                "original_filename": d.original_filename,
                "content_type": d.content_type,
                "size_bytes": d.size_bytes,
                "uploaded_by": d.uploaded_by,
                "uploaded_at": d.uploaded_at.isoformat(),
                "file_url": d.file.url if d.file else None,
            }
            for d in documents
        ],
        "notes": [
            {
                "id": n.pk,
                "body": n.body,
                "created_by": n.created_by,
                "created_at": n.created_at.isoformat(),
            }
            for n in notes
        ],
        "decisions": [
            {
                "id": d.pk,
                "decision": d.decision,
                "notes": d.notes,
                "decided_by": d.decided_by,
                "decided_at": d.decided_at.isoformat(),
            }
            for d in decisions
        ],
        "audit_events": [
            {
                "id": e.pk,
                "event_type": e.event_type,
                "actor": e.actor,
                "payload": e.payload,
                "created_at": e.created_at.isoformat(),
            }
            for e in audit_events
        ],
    }


def load_claim_for_export(*, claim_id: int) -> Claim:
    """Load a claim with all related data needed for export.

    Args:
        claim_id: Claim primary key.

    Returns:
        Fully loaded Claim instance.
    """
    return (
        Claim.objects.select_related("policy", "policy__holder", "sla_clock")
        .prefetch_related(
            Prefetch("documents", queryset=ClaimDocument.objects.order_by("uploaded_at")),
            Prefetch("notes", queryset=InternalNote.objects.order_by("created_at")),
            Prefetch("decisions", queryset=ReviewDecision.objects.order_by("decided_at")),
            Prefetch("audit_events", queryset=AuditEvent.objects.order_by("created_at")),
        )
        .get(pk=claim_id)
    )
