# path: policylens/apps/claims/management/commands/sweep_sla_breaches.py
"""
Sweep SLA breaches and record evidence.

This command:
- Marks breached_at for clocks whose due_at has passed and are not decided.
- Appends SLA_BREACHED audit events for evidence.

Designed for periodic execution in production (cron/worker) later.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from policylens.apps.claims import sla
from policylens.apps.claims.services import append_audit_event


class Command(BaseCommand):
    """Sweep and record SLA breaches."""

    help = "Mark breached SLA clocks and append SLA_BREACHED audit evidence."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        """Run the sweep."""
        now = timezone.now()
        breached = list(sla.find_breached_clocks(now=now))

        updated_count = 0
        for clock in breached:
            if clock.breached_at is None:
                clock.breached_at = now
                clock.save(update_fields=["breached_at"])
                append_audit_event(
                    claim=clock.claim,
                    event_type="SLA_BREACHED",
                    actor="system",
                    payload={
                        "due_at": clock.due_at.isoformat() if clock.due_at else None,
                        "breached_at": now.isoformat(),
                    },
                )
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Marked {updated_count} SLA breaches."))
