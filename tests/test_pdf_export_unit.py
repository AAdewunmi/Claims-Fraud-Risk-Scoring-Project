# path: tests/test_pdf_export_unit.py
"""Unit tests for deterministic PDF export helpers."""

from __future__ import annotations

from datetime import datetime

from policylens.apps.claims.pdf_export import _pdf_escape, build_claim_audit_export_pdf


def test_pdf_escape_normalizes_special_characters() -> None:
    """Escaping should be deterministic and remove newline/carriage characters."""
    raw = r"Line(1)\end" + "\n" + "next\rline"
    escaped = _pdf_escape(raw)

    assert "\\(" in escaped
    assert "\\)" in escaped
    assert "\\\\" in escaped
    assert "\n" not in escaped
    assert "\r" not in escaped


def test_build_claim_audit_export_pdf_handles_datetime_and_overflow_sections() -> None:
    """PDF builder should cover datetime export and overflow summary branches."""
    payload = {
        "export_version": "v1",
        "exported_at": datetime(2026, 3, 6, 12, 0, 0),
        "claim": {
            "id": 42,
            "claim_type": "CLAIM",
            "status": "NEW",
            "priority": "HIGH",
            "created_by": "tester",
        },
        "policy": {"policy_number": "PL-42", "product_type": "Home Insurance"},
        "policy_holder": {"full_name": "Test Holder", "email": "holder@example.com"},
        "documents": [
            {
                "original_filename": f"doc-{idx}.txt",
                "content_type": "text/plain",
                "size_bytes": 10 + idx,
            }
            for idx in range(13)
        ],
        "notes": [],
        "decisions": [],
        "audit_events": [
            {"created_at": f"2026-03-06T12:00:{idx:02d}Z", "event_type": "EV", "actor": "tester"}
            for idx in range(9)
        ],
    }

    pdf_bytes = build_claim_audit_export_pdf(payload=payload)

    assert pdf_bytes.startswith(b"%PDF")
    # Overflow summary lines for document/event truncation should be present.
    assert b"... 1 more" in pdf_bytes
