"""
Create deterministic demo users and seed data for PolicyLens.

Sprint 6 goals
- Create demo admin, reviewer, and customer users.
- Ensure reviewer queue has enough claims to demonstrate pagination.
- Keep demo customer claims simple: one customer, one claim.

Idempotency
- The command can be run repeatedly.
- Users are created if missing and their passwords are set on each run.
- Reviewer claims are created only until the minimum count is satisfied.
- Customer claims are normalized to exactly one claim for demo_customer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from policylens.apps.claims.models import Claim, Policy, PolicyHolder, SlaClock


@dataclass(frozen=True)
class DemoUserSpec:
    """Definition of a demo user and its role group membership."""

    username: str
    email: str
    group_name: str
    password: str


class Command(BaseCommand):
    """
    Create demo users and seed demo claims for Sprint 6.

    Demo users
    - demo_admin (group: admin)
    - demo_reviewer (group: reviewer)
    - demo_customer (group: customer)

    Seed data
    - At least 16 reviewer-queue-visible claims (not customer-owned)
    - Exactly 1 customer-owned claim (owned by demo_customer)
    """

    help = "Create PolicyLens demo users, reviewer queue claims, and a single demo customer claim."

    DEMO_PASSWORD = "pass-12345-strong"

    REVIEWER_SEED_MARKER = "demo-reviewer-seed"
    CUSTOMER_SEED_MARKER = "demo-customer-seed"

    MIN_REVIEWER_QUEUE_CLAIMS = 20
    TARGET_CUSTOMER_OWNED_CLAIMS = 1

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Entrypoint for the management command.

        Prints a deterministic summary at the end so the command can be used in
        a repeatable demo runbook.
        """
        with transaction.atomic():
            admin_group, reviewer_group, customer_group = self._ensure_groups()

            admin_user = self._ensure_user(
                DemoUserSpec(
                    username="demo_admin",
                    email="demo_admin@example.com",
                    group_name=admin_group.name,
                    password=self.DEMO_PASSWORD,
                )
            )
            reviewer_user = self._ensure_user(
                DemoUserSpec(
                    username="demo_reviewer",
                    email="demo_reviewer@example.com",
                    group_name=reviewer_group.name,
                    password=self.DEMO_PASSWORD,
                )
            )
            customer_user = self._ensure_user(
                DemoUserSpec(
                    username="demo_customer",
                    email="demo_customer@example.com",
                    group_name=customer_group.name,
                    password=self.DEMO_PASSWORD,
                )
            )

            reviewer_policy = self._ensure_policy_for_email(
                email="reviewer_demo_holder@example.com",
                policy_number="DEMO-PL-REVIEWER-0001",
            )
            customer_policy = self._ensure_policy_for_email(
                email=customer_user.email,
                policy_number="DEMO-PL-CUSTOMER-0001",
            )

            created_reviewer = self._ensure_reviewer_queue_claims(reviewer_policy)
            created_customer, pruned_customer = self._ensure_customer_owned_claims(
                customer_policy, customer_user
            )

        self.stdout.write("Demo users created or updated")
        self.stdout.write(f"admin_user={admin_user.username} password={self.DEMO_PASSWORD}")
        self.stdout.write(f"reviewer_user={reviewer_user.username} password={self.DEMO_PASSWORD}")
        self.stdout.write(f"customer_user={customer_user.username} password={self.DEMO_PASSWORD}")
        self.stdout.write("")
        self.stdout.write("Demo seed status")
        self.stdout.write(f"created_reviewer_queue_claims={created_reviewer}")
        self.stdout.write(f"created_customer_owned_claims={created_customer}")
        self.stdout.write(f"pruned_customer_owned_claims={pruned_customer}")
        self.stdout.write(f"total_reviewer_queue_claims={self._reviewer_queue_claim_count()}")
        self.stdout.write(
            f"total_customer_owned_claims={self._customer_owned_claim_count(customer_user)}"
        )

    def _ensure_groups(self) -> tuple[Group, Group, Group]:
        """Ensure the standard Sprint 6 groups exist."""
        admin_group, _ = Group.objects.get_or_create(name="admin")
        reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
        customer_group, _ = Group.objects.get_or_create(name="customer")
        return admin_group, reviewer_group, customer_group

    def _ensure_user(self, spec: DemoUserSpec):
        """
        Create or update a demo user and assign group membership.

        Password is set on each run to keep demo access deterministic.
        """
        User = get_user_model()
        user, _ = User.objects.get_or_create(username=spec.username, defaults={"email": spec.email})

        if getattr(user, "email", "") != spec.email:
            user.email = spec.email

        user.set_password(spec.password)
        user.save()

        group = Group.objects.get(name=spec.group_name)
        user.groups.set([group])

        return user

    def _ensure_policy_for_email(self, *, email: str, policy_number: str) -> Policy:
        """
        Ensure a PolicyHolder and Policy exist for a given email.

        Customer ownership in Sprint 6 is satisfied by policy holder email matching
        the customer's email, and by claim.created_by matching the customer's username.
        """
        holder, _ = PolicyHolder.objects.get_or_create(
            email=email,
            defaults={"full_name": "Demo User", "phone": ""},
        )
        policy, _ = Policy.objects.get_or_create(
            policy_number=policy_number,
            defaults={
                "holder": holder,
                "product_type": "Home Insurance",
                "status": Policy.Status.ACTIVE,
            },
        )
        return policy

    def _reviewer_queue_claim_count(self) -> int:
        """Count reviewer-queue-visible claims created by this demo seed."""
        return Claim.objects.filter(created_by=self.REVIEWER_SEED_MARKER).count()

    def _customer_owned_claim_count(self, customer_user: Any) -> int:
        """
        Count customer-owned claims for the given demo customer user.

        Customer console ownership currently resolves by `created_by == username` first,
        so this count uses the same contract.
        """
        return Claim.objects.filter(created_by=customer_user.username).count()

    def _ensure_reviewer_queue_claims(self, policy: Policy) -> int:
        """
        Ensure enough claims exist to demonstrate pagination in the reviewer queue.

        These claims are not owned by the demo customer. They exist solely to
        guarantee two pages on /ops/queue/.
        """
        existing = self._reviewer_queue_claim_count()
        to_create = max(0, self.MIN_REVIEWER_QUEUE_CLAIMS - existing)

        created = 0
        for i in range(to_create):
            claim = Claim.objects.create(
                policy=policy,
                claim_type=Claim.Type.CLAIM,
                status=Claim.Status.NEW,
                priority=Claim.Priority.NORMAL,
                summary=f"Reviewer demo claim {existing + i}",
                created_by=self.REVIEWER_SEED_MARKER,
            )
            SlaClock.objects.get_or_create(
                claim=claim,
                defaults={"due_at": timezone.now() + timedelta(days=1)},
            )
            created += 1

        return created

    def _ensure_customer_owned_claims(self, policy: Policy, customer_user: Any) -> tuple[int, int]:
        """
        Enforce a single customer-owned claim for the demo customer.

        Ownership contract
        - created_by matches customer username

        Returns:
        - created_count
        - pruned_count
        """
        qs = Claim.objects.filter(created_by=customer_user.username).order_by("-created_at", "-id")
        existing = qs.count()

        pruned = 0
        if existing > self.TARGET_CUSTOMER_OWNED_CLAIMS:
            keep = self.TARGET_CUSTOMER_OWNED_CLAIMS
            ids_to_delete = list(qs.values_list("id", flat=True)[keep:])
            if ids_to_delete:
                pruned, _ = Claim.objects.filter(id__in=ids_to_delete).delete()

        existing_after_prune = Claim.objects.filter(created_by=customer_user.username).count()
        to_create = max(0, self.TARGET_CUSTOMER_OWNED_CLAIMS - existing_after_prune)

        created = 0
        for i in range(to_create):
            claim = Claim.objects.create(
                policy=policy,
                claim_type=Claim.Type.CLAIM,
                status=Claim.Status.NEW,
                priority=Claim.Priority.NORMAL,
                summary=f"Customer demo claim {existing + i}",
                created_by=customer_user.username,
            )
            SlaClock.objects.get_or_create(
                claim=claim,
                defaults={"due_at": timezone.now() + timedelta(days=1)},
            )
            created += 1

        return created, pruned
