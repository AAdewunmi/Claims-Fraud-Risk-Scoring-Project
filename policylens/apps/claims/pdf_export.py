# path: policylens/apps/claims/pdf_export.py
"""PDF export helpers for claim audit evidence bundles."""

from __future__ import annotations

import json


def _escape_pdf_text(value: str) -> str:
    """Escape text for safe use in PDF string literals."""
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_content_stream(payload: dict) -> str:
    """Build a deterministic single-page text stream for the PDF."""
    serialized = json.dumps(payload, sort_keys=True, indent=2)
    lines = [
        "PolicyLens Audit Export",
        "",
    ]
    lines.extend(serialized.splitlines())

    stream_lines: list[str] = ["BT", "/F1 10 Tf", "50 760 Td", "14 TL"]
    for line in lines[:140]:
        safe = _escape_pdf_text(line)
        stream_lines.append(f"({safe}) Tj")
        stream_lines.append("T*")
    stream_lines.append("ET")
    return "\n".join(stream_lines) + "\n"


def build_claim_audit_export_pdf(*, payload: dict) -> bytes:
    """Return deterministic PDF bytes for an audit-export payload."""
    content_stream = _build_content_stream(payload)
    stream_bytes = content_stream.encode("utf-8")

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R "
            "/MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 5 0 R >> >> "
            "/Contents 4 0 R >>"
        ),
        f"<< /Length {len(stream_bytes)} >>\nstream\n{content_stream}endstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    chunks: list[bytes] = [b"%PDF-1.4\n%----\n"]
    offsets: list[int] = [0]

    for idx, obj in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{idx} 0 obj\n".encode("ascii"))
        chunks.append(obj.encode("utf-8"))
        chunks.append(b"\nendobj\n")

    xref_offset = sum(len(chunk) for chunk in chunks)
    xref_lines = ["xref", f"0 {len(objects) + 1}", "0000000000 65535 f "]
    xref_lines.extend(f"{offset:010} 00000 n " for offset in offsets[1:])
    chunks.append(("\n".join(xref_lines) + "\n").encode("ascii"))

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    )
    chunks.append(trailer.encode("ascii"))

    return b"".join(chunks)
