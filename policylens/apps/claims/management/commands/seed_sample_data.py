# path: policylens/apps/claims/management/commands/seed_sample_data.py
"""
Seed deterministic sample data for local development.

Week 2 adds:
- Default reviewer and admin groups
- Sample users assigned to those roles

This command is designed for repeatable demos and for week 5 UI development.
"""

from __future__ import annotations

import random
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from policylens.apps.claims.models import Claim, Policy, PolicyHolder, ReviewDecision
from policylens.apps.claims.services import add_decision, add_note, create_claim

User = get_user_model()


class Command(BaseCommand):
    """Seed sample data into the database."""

    help = "Seed deterministic sample data for PolicyLens."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        """Run the seed workflow."""
        rng = random.Random(42)

        reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
        admin_group, _ = Group.objects.get_or_create(name="admin")

        reviewer, reviewer_created = User.objects.get_or_create(username="reviewer1")
        if reviewer_created:
            reviewer.set_password("password123")
            reviewer.save()
        reviewer.groups.add(reviewer_group)

        admin, admin_created = User.objects.get_or_create(
            username="admin1",
            defaults={"is_staff": True, "is_superuser": False},
        )
        if admin_created:
            admin.set_password("password123")
            admin.save()
        admin.groups.add(admin_group)

        holders = []
        for i in range(5):
            email = f"holder{i+1}@example.com"
            holder = PolicyHolder.objects.filter(email=email).order_by(
                "pk"
            ).first() or PolicyHolder.objects.create(
                full_name=f"Sample Holder {i+1}",
                email=email,
                phone=f"+44 7700 900{i:03d}",
            )
            holders.append(holder)

        policies = []
        for i, holder in enumerate(holders, start=1):
            policy_number = f"PL-{1000 + i}"
            policy = Policy.objects.filter(policy_number=policy_number).order_by(
                "pk"
            ).first() or Policy.objects.create(
                holder=holder,
                policy_number=policy_number,
                product_type=rng.choice(
                    [
                        "Home Insurance",
                        "Motor Insurance",
                        "Travel Insurance",
                    ]
                ),
                status=Policy.Status.ACTIVE,
                effective_date=date(2024, 1, 1),
            )
            policies.append(policy)

        created_claims = []
        claim_specs = []
        for _ in range(10):
            policy = rng.choice(policies)
            claim_type = rng.choice([Claim.Type.CLAIM, Claim.Type.POLICY_CHANGE])
            priority = rng.choice(
                [
                    Claim.Priority.LOW,
                    Claim.Priority.NORMAL,
                    Claim.Priority.HIGH,
                ]
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
            claim_specs.append((policy, claim_type, priority, summary))

        for policy, claim_type, priority, summary in claim_specs:
            claim = (
                Claim.objects.filter(
                    policy=policy,
                    claim_type=claim_type,
                    priority=priority,
                    summary=summary,
                    created_by="seed",
                )
                .order_by("pk")
                .first()
            )
            if claim is None:
                claim = create_claim(
                    policy=policy,
                    claim_type=claim_type,
                    priority=priority,
                    summary=summary,
                    actor="seed",
                )
            created_claims.append(claim)

        # Add a few notes and one decision for realism.
        for claim in created_claims[:3]:
            if not claim.notes.filter(
                body="Seeded note for timeline realism.",
                created_by=reviewer.username,
            ).exists():
                add_note(
                    claim=claim,
                    body="Seeded note for timeline realism.",
                    actor=reviewer.username,
                )

        if created_claims and not created_claims[0].decisions.exists():
            add_decision(
                claim=created_claims[0],
                decision=ReviewDecision.Decision.REQUEST_INFO,
                notes="Seeded request for more info.",
                actor=reviewer.username,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded roles (reviewer, admin), users (reviewer1/admin1), "
                "holders, policies, claims."
            )
        )
