# path: policylens/apps/claims/management/commands/backfill_sla_clocks.py
"""
Backfill SLA clocks for existing claims.

Uses claim.created_at as the deterministic anchor.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.claims import sla
from apps.claims.models import Claim
from apps.claims.services import append_audit_event


class Command(BaseCommand):
    """Create missing SLA clocks for existing claims."""

    help = "Backfill SLA clocks for claims that are missing them."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        """Run the backfill."""
        missing = Claim.objects.filter(sla_clock__isnull=True).order_by("created_at")
        created_count = 0

        for claim in missing:
            clock = sla.ensure_sla_clock_exists(claim=claim)
            append_audit_event(
                claim=claim,
                event_type="SLA_STARTED",
                actor="system",
                payload={
                    "started_at": clock.started_at.isoformat(),
                    "due_at": clock.due_at.isoformat() if clock.due_at else None,
                    "backfilled": True,
                },
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Backfilled SLA clocks for {created_count} claims."))
