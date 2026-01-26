# path: policylens/apps/claims/services.py
"""
Domain services for claims.

This module centralises business behaviour so that API and UI share the same logic.
Week 2 adds document upload, internal notes, and decisions.
"""

from __future__ import annotations

from typing import Any

from django.core.files.base import File
from django.db import transaction

from policylens.apps.claims.models import (
    AuditEvent,
    Claim,
    ClaimDocument,
    InternalNote,
    Policy,
    ReviewDecision,
)


class DomainRuleViolation(Exception):
    """Raised when a workflow rule is violated.

    The API layer converts this into a client-facing error response.
    """


def append_audit_event(*, claim: Claim, event_type: str, actor: str, payload: dict[str, Any]) -> AuditEvent:
    """Append an audit event for a claim."""
    return AuditEvent.objects.create(
        claim=claim,
        event_type=event_type,
        actor=actor,
        payload=payload,
    )


@transaction.atomic
def create_claim(
    *,
    policy: Policy,
    claim_type: str,
    priority: str,
    summary: str,
    actor: str,
) -> Claim:
    """Create a claim and append an initial audit event."""
    claim = Claim.objects.create(
        policy=policy,
        claim_type=claim_type,
        priority=priority,
        summary=summary,
        created_by=actor,
    )

    append_audit_event(
        claim=claim,
        event_type="CLAIM_CREATED",
        actor=actor,
        payload={
            "policy_number": policy.policy_number,
            "claim_type": claim_type,
            "priority": priority,
        },
    )

    return claim


def _assert_claim_not_decided(*, claim: Claim) -> None:
    """Prevent mutations that should not happen after a final decision."""
    if claim.status == Claim.Status.DECIDED:
        raise DomainRuleViolation("Claim is already decided. No further workflow actions are allowed.")


@transaction.atomic
def add_document(
    *,
    claim: Claim,
    uploaded_file: File,
    original_filename: str,
    content_type: str,
    actor: str,
) -> ClaimDocument:
    """Attach a document to a claim and append an audit event."""
    _assert_claim_not_decided(claim=claim)

    size_bytes = getattr(uploaded_file, "size", 0) or 0
    doc = ClaimDocument.objects.create(
        claim=claim,
        file=uploaded_file,
        original_filename=original_filename,
        content_type=content_type or "",
        size_bytes=size_bytes,
        uploaded_by=actor,
    )

    append_audit_event(
        claim=claim,
        event_type="DOCUMENT_UPLOADED",
        actor=actor,
        payload={
            "document_id": doc.pk,
            "original_filename": original_filename,
            "content_type": content_type or "",
            "size_bytes": size_bytes,
        },
    )
    return doc


@transaction.atomic
def add_note(*, claim: Claim, body: str, actor: str) -> InternalNote:
    """Add an internal note to a claim and append an audit event."""
    if not body or not body.strip():
        raise DomainRuleViolation("Note body is required.")

    note = InternalNote.objects.create(claim=claim, body=body.strip(), created_by=actor)

    append_audit_event(
        claim=claim,
        event_type="NOTE_ADDED",
        actor=actor,
        payload={
            "note_id": note.pk,
            "length": len(note.body),
        },
    )
    return note


@transaction.atomic
def add_decision(
    *,
    claim: Claim,
    decision: str,
    notes: str,
    actor: str,
) -> ReviewDecision:
    """Record a decision for a claim, update claim status, and append an audit event."""
    _assert_claim_not_decided(claim=claim)

    record = ReviewDecision.objects.create(
        claim=claim,
        decision=decision,
        notes=notes or "",
        decided_by=actor,
    )

    # Minimal deterministic workflow rules for Week 2.
    if decision == ReviewDecision.Decision.REQUEST_INFO:
        claim.status = Claim.Status.IN_REVIEW
    else:
        claim.status = Claim.Status.DECIDED
    claim.save(update_fields=["status", "updated_at"])

    append_audit_event(
        claim=claim,
        event_type="DECISION_RECORDED",
        actor=actor,
        payload={
            "decision_id": record.pk,
            "decision": decision,
        },
    )
    return record
