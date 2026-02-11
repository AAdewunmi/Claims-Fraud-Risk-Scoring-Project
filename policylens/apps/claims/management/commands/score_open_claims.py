# path: policylens/apps/claims/management/commands/score_open_claims.py
"""
Score all open claims using the active ML model version.

Safe to re-run:
- Updates MlScore via update_or_create
- Appends an ML_SCORED audit event each time (evidence of scoring activity)
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from policylens.apps.claims.ml.scoring import ModelNotReady, score_claim
from policylens.apps.claims.models import Claim


class Command(BaseCommand):
    """Score all open claims."""

    help = "Score all open claims and persist MlScore."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--actor", default="system", help="Actor used in audit events.")

    def handle(self, *args, **options) -> None:
        actor = str(options["actor"])
        claims = Claim.objects.filter(
            status__in=[Claim.Status.NEW, Claim.Status.IN_REVIEW]
        ).order_by("created_at")

        scored = 0
        for claim in claims:
            try:
                score_claim(claim=claim, actor=actor)
                scored += 1
            except ModelNotReady as exc:
                self.stderr.write(self.style.ERROR(f"Model not ready: {exc}"))
                return

        self.stdout.write(self.style.SUCCESS(f"Scored {scored} open claims."))
