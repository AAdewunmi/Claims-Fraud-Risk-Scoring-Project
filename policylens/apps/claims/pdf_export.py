# path: policylens/apps/claims/pdf_export.py
"""
Deterministic PDF export generator for claim audit evidence.

This module intentionally avoids external PDF libraries to keep the runtime dependency
surface minimal and to keep output stable across environments.

The PDF emitted is a simple, single-page document with Helvetica text. The goal is
evidence portability and a predictable bytes contract, not layout richness.

Contract
- Returned bytes must begin with "%PDF"
- Output must be deterministic for a given input payload ordering
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


def _pdf_escape(text: str) -> str:
    """
    Escape a string for inclusion in a PDF literal string.

    Args:
        text: Raw text.

    Returns:
        PDF-safe string with backslashes and parentheses escaped.
    """
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\n", " ")
        .replace("\r", " ")
    )


@dataclass(frozen=True)
class _PdfObject:
    """
    A single PDF indirect object.

    Attributes:
        body: Raw bytes of the object body excluding the 'n 0 obj' wrapper.
    """

    body: bytes


def _build_minimal_pdf(lines: Iterable[str]) -> bytes:
    """
    Build a minimal single-page PDF containing the supplied lines.

    Args:
        lines: Lines to render from top to bottom.

    Returns:
        PDF bytes.
    """
    rendered_lines = [_pdf_escape(line) for line in lines]

    # Build a simple content stream.
    #  - Helvetica font (F1)
    #  - Font size 11
    #  - Start near top-left, move down with a stable leading
    font_size = 11
    leading = 14
    x_start = 54
    y_start = 780

    stream_lines: list[str] = [
        "BT",
        f"/F1 {font_size} Tf",
        f"{x_start} {y_start} Td",
        f"{leading} TL",
    ]

    for idx, line in enumerate(rendered_lines):
        if idx == 0:
            stream_lines.append(f"({line}) Tj")
        else:
            stream_lines.append("T*")
            stream_lines.append(f"({line}) Tj")

    stream_lines.append("ET")

    stream = ("\n".join(stream_lines) + "\n").encode("utf-8")

    objects: list[_PdfObject] = []

    # 1: Catalog
    objects.append(_PdfObject(b"<< /Type /Catalog /Pages 2 0 R >>"))

    # 2: Pages
    objects.append(_PdfObject(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))

    # 3: Page
    objects.append(
        _PdfObject(
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>"
        )
    )

    # 4: Contents stream
    objects.append(
        _PdfObject(
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"endstream"
        )
    )

    # 5: Font
    objects.append(_PdfObject(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n")
    pdf.extend(b"%\xe2\xe3\xcf\xd3\n")

    offsets: list[int] = [0]

    for obj_num, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{obj_num} 0 obj\n".encode("ascii"))
        pdf.extend(obj.body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)

    pdf.extend(b"xref\n")
    pdf.extend(f"0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")

    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    pdf.extend(b"trailer\n")
    pdf.extend(f"<< /Size {len(offsets)} /Root 1 0 R >>\n".encode("ascii"))
    pdf.extend(b"startxref\n")
    pdf.extend(f"{xref_offset}\n".encode("ascii"))
    pdf.extend(b"%%EOF\n")

    return bytes(pdf)


def build_claim_audit_export_pdf(*, payload: dict) -> bytes:
    """
    Render a claim audit export payload to a deterministic PDF.

    Args:
        payload: The dict returned by the JSON audit export builder.

    Returns:
        PDF bytes.
    """
    exported_at = payload.get("exported_at")
    exported_at_display = exported_at
    if isinstance(exported_at, str):
        exported_at_display = exported_at
    elif isinstance(exported_at, datetime):
        exported_at_display = exported_at.isoformat()

    claim = payload.get("claim", {}) or {}
    policy = payload.get("policy", {}) or {}
    holder = payload.get("policy_holder", {}) or {}

    documents = payload.get("documents", []) or []
    notes = payload.get("notes", []) or []
    decisions = payload.get("decisions", []) or []
    audit_events = payload.get("audit_events", []) or []

    lines: list[str] = []
    lines.append("PolicyLens claim audit export")
    lines.append(f"export_version: {payload.get('export_version', 'unknown')}")
    lines.append(f"exported_at: {exported_at_display}")
    lines.append("")
    lines.append(f"claim_id: {claim.get('id')}")
    lines.append(f"claim_type: {claim.get('claim_type')}")
    lines.append(f"status: {claim.get('status')}")
    lines.append(f"priority: {claim.get('priority')}")
    lines.append(f"created_by: {claim.get('created_by')}")
    lines.append("")
    lines.append(f"policy_number: {policy.get('policy_number')}")
    lines.append(f"product_type: {policy.get('product_type')}")
    lines.append("")
    lines.append(f"policy_holder: {holder.get('full_name')}")
    lines.append(f"policy_holder_email: {holder.get('email')}")
    lines.append("")
    lines.append(f"documents_count: {len(documents)}")
    lines.append(f"notes_count: {len(notes)}")
    lines.append(f"decisions_count: {len(decisions)}")
    lines.append(f"audit_events_count: {len(audit_events)}")
    lines.append("")
    lines.append("documents:")
    for doc in documents[:12]:
        lines.append(
            f"- {doc.get('original_filename')} ({doc.get('content_type')}, {doc.get('size_bytes')} bytes)"
        )

    if len(documents) > 12:
        lines.append(f"- ... {len(documents) - 12} more")

    lines.append("")
    lines.append("audit_events (first 8):")
    for ev in audit_events[:8]:
        lines.append(f"- {ev.get('created_at')} {ev.get('event_type')} actor={ev.get('actor')}")

    if len(audit_events) > 8:
        lines.append(f"- ... {len(audit_events) - 8} more")

    return _build_minimal_pdf(lines)
