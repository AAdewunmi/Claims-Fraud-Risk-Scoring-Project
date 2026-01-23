# path: policylens/apps/claims/management/commands/seed_sample_data.py
"""
Seed deterministic sample data for local development.

This command is designed for repeatable demos and for week 5 UI development.
"""

from __future__ import annotations

import random
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from policylens.apps.claims.models import Claim, Policy, PolicyHolder
from policylens.apps.claims.services import append_audit_event, create_claim


class Command(BaseCommand):
    """Seed sample data into the database."""

    help = "Seed deterministic sample data for PolicyLens."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        """Run the seed workflow."""
        rng = random.Random(42)

        holders = []
        for i in range(5):
            holder = PolicyHolder.objects.create(
                full_name=f"Sample Holder {i+1}",
                email=f"holder{i+1}@example.com",
                phone=f"+44 7700 900{i:03d}",
            )
            holders.append(holder)

        policies = []
        for i, holder in enumerate(holders, start=1):
            policy = Policy.objects.create(
                holder=holder,
                policy_number=f"PL-{1000 + i}",
                product_type=rng.choice(
                    ["Home Insurance", "Motor Insurance", "Travel Insurance"]
                ),
                status=Policy.Status.ACTIVE,
                effective_date=date(2024, 1, 1),
            )
            policies.append(policy)

        created_claims = []
        for i in range(10):
            policy = rng.choice(policies)
            claim_type = rng.choice(
                [Claim.Type.CLAIM, Claim.Type.POLICY_CHANGE]
            )
            priority = rng.choice(
                [Claim.Priority.LOW,
                 Claim.Priority.NORMAL,
                 Claim.Priority.HIGH]
            )
            summary = rng.choice(
                [
                    "Customer submitted initial documents.",
                    "Missing proof of address.",
                    "Upload includes unclear photo.",
                    "Policy change request with partial details.",
                    "Claim notes mention third party involvement.",
                ]
            )
            claim = create_claim(
                policy=policy,
                claim_type=claim_type,
                priority=priority,
                summary=summary,
                actor="seed",
            )
            created_claims.append(claim)

        # Add one extra event for realism
        for claim in created_claims[:3]:
            append_audit_event(
                claim=claim,
                event_type="NOTE_ADDED",
                actor="seed",
                payload={"note": "Seeded note for timeline realism."},
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded "
                f"{len(holders)} holders, "
                f"{len(policies)} policies, "
                f"{len(created_claims)} claims."
            )
        )
