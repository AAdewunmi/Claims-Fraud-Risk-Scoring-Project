# path: policylens/apps/core/idempotency.py
"""
Idempotency utilities.

Decision endpoint idempotency uses:
- Idempotency-Key header
- Request body hash
"""

from __future__ import annotations

import hashlib

from django.db import IntegrityError, transaction

from apps.core.models import IdempotencyRecord


class IdempotencyConflict(Exception):
    """Raised when the same idempotency key is reused with a different payload."""


def request_hash_from_bytes(body: bytes) -> str:
    """Return sha256 hex digest for request body bytes."""
    return hashlib.sha256(body).hexdigest()


def find_record(*, user, key: str, method: str, path: str) -> IdempotencyRecord | None:
    """Find an existing idempotency record for this user and endpoint."""
    return IdempotencyRecord.objects.filter(user=user, key=key, method=method, path=path).first()


@transaction.atomic
def store_record(
    *,
    user,
    key: str,
    method: str,
    path: str,
    request_hash: str,
    response_status: int,
    response_body: dict,
) -> IdempotencyRecord:
    """Persist the idempotency record for future replays."""
    try:
        return IdempotencyRecord.objects.create(
            user=user,
            key=key,
            method=method,
            path=path,
            request_hash=request_hash,
            response_status=response_status,
            response_body=response_body,
        )
    except IntegrityError as exc:
        # Another request may have created it concurrently.
        existing = find_record(user=user, key=key, method=method, path=path)
        if existing is None:
            raise
        if existing.request_hash != request_hash:
            raise IdempotencyConflict("Idempotency key reuse with different payload.") from exc
        return existing
