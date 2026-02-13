"""
Unit tests for idempotency helpers.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.db import IntegrityError

from policylens.apps.core.idempotency import (
    IdempotencyConflict,
    request_hash_from_bytes,
    store_record,
)


def test_request_hash_from_bytes_is_stable_for_same_payload():
    """Hashing the same bytes should produce the same digest."""
    payload = b'{"decision":"APPROVE"}'
    assert request_hash_from_bytes(payload) == request_hash_from_bytes(payload)


@pytest.mark.django_db
def test_store_record_returns_existing_on_integrity_error_with_same_hash(monkeypatch):
    """Concurrent create should reuse existing record when hashes match."""
    existing = SimpleNamespace(request_hash="abc123")

    def fake_create(**kwargs):
        raise IntegrityError("duplicate key")

    def fake_find_record(**kwargs):
        return existing

    monkeypatch.setattr(
        "policylens.apps.core.idempotency.IdempotencyRecord.objects.create",
        fake_create,
    )
    monkeypatch.setattr(
        "policylens.apps.core.idempotency.find_record",
        fake_find_record,
    )

    record = store_record(
        user=object(),
        key="idem-key",
        method="POST",
        path="/api/claims/1/decisions/",
        request_hash="abc123",
        response_status=201,
        response_body={"id": 1},
    )

    assert record is existing


@pytest.mark.django_db
def test_store_record_raises_conflict_on_integrity_error_with_different_hash(
    monkeypatch,
):
    """Concurrent create with different payload hash should raise conflict."""
    existing = SimpleNamespace(request_hash="first-hash")

    def fake_create(**kwargs):
        raise IntegrityError("duplicate key")

    def fake_find_record(**kwargs):
        return existing

    monkeypatch.setattr(
        "policylens.apps.core.idempotency.IdempotencyRecord.objects.create",
        fake_create,
    )
    monkeypatch.setattr(
        "policylens.apps.core.idempotency.find_record",
        fake_find_record,
    )

    with pytest.raises(IdempotencyConflict):
        store_record(
            user=object(),
            key="idem-key",
            method="POST",
            path="/api/claims/1/decisions/",
            request_hash="second-hash",
            response_status=201,
            response_body={"id": 1},
        )


@pytest.mark.django_db
def test_store_record_reraises_integrity_error_when_existing_record_not_found(
    monkeypatch,
):
    """IntegrityError should bubble up if fallback lookup cannot find a record."""

    def fake_create(**kwargs):
        raise IntegrityError("duplicate key")

    def fake_find_record(**kwargs):
        return None

    monkeypatch.setattr(
        "policylens.apps.core.idempotency.IdempotencyRecord.objects.create",
        fake_create,
    )
    monkeypatch.setattr(
        "policylens.apps.core.idempotency.find_record",
        fake_find_record,
    )

    with pytest.raises(IntegrityError):
        store_record(
            user=object(),
            key="idem-key",
            method="POST",
            path="/api/claims/1/decisions/",
            request_hash="abc123",
            response_status=201,
            response_body={"id": 1},
        )
