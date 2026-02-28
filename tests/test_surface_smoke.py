"""
DB-hitting surface smoke tests for Week 6.

Goals
- Log in per role using the surface entry points.
- Hit paginated list pages using page=1 and page=2:
  - reviewer queue: /ops/queue/
  - customer claim list: /customer/

This test is intentionally shallow: it proves the surfaces route, gate, and paginate.
Deeper contract tests live in the dedicated pagination/ownership test modules.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from policylens.apps.claims.models import Claim, Policy, PolicyHolder, SlaClock

pytestmark = pytest.mark.django_db


DEMO_PASSWORD = "pass-12345-strong"


def _ensure_groups() -> dict[str, Group]:
    """Ensure standard role groups exist for the smoke test."""
    admin_group, _ = Group.objects.get_or_create(name="admin")
    reviewer_group, _ = Group.objects.get_or_create(name="reviewer")
    customer_group, _ = Group.objects.get_or_create(name="customer")
    return {"admin": admin_group, "reviewer": reviewer_group, "customer": customer_group}


def _create_user(*, username: str, email: str, group: Group):
    """Create a user and assign it to exactly one role group."""
    User = get_user_model()
    user = User.objects.create_user(username=username, email=email, password=DEMO_PASSWORD)
    user.groups.set([group])
    return user


def _policy_for_email(*, email: str, policy_number: str) -> Policy:
    """Create a policy holder and policy for seeding demo claims."""
    holder, _ = PolicyHolder.objects.get_or_create(
        email=email, defaults={"full_name": "Smoke User", "phone": ""}
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


def _seed_claims_for_pagination(
    *, customer_user, customer_policy, reviewer_policy, count: int = 16
) -> None:
    """
    Seed enough claims to demonstrate pagination on both surfaces.

    Customer ownership contract in the app:
    - policy holder email matches customer email
    - created_by matches customer username
    """
    existing_customer = Claim.objects.filter(
        policy=customer_policy, created_by=customer_user.username
    ).count()
    to_create_customer = max(0, count - existing_customer)

    for i in range(to_create_customer):
        claim = Claim.objects.create(
            policy=customer_policy,
            claim_type=Claim.Type.CLAIM,
            status=Claim.Status.NEW,
            priority=Claim.Priority.NORMAL,
            summary=f"Smoke customer claim {i}",
            created_by=customer_user.username,
        )
        SlaClock.objects.get_or_create(
            claim=claim, defaults={"due_at": timezone.now() + timedelta(days=1)}
        )

    existing_queue_only = Claim.objects.filter(
        policy=reviewer_policy, created_by="smoke-reviewer-seed"
    ).count()
    to_create_queue_only = max(0, count - existing_queue_only)

    for i in range(to_create_queue_only):
        claim = Claim.objects.create(
            policy=reviewer_policy,
            claim_type=Claim.Type.CLAIM,
            status=Claim.Status.NEW,
            priority=Claim.Priority.NORMAL,
            summary=f"Smoke reviewer claim {i}",
            created_by="smoke-reviewer-seed",
        )
        SlaClock.objects.get_or_create(
            claim=claim, defaults={"due_at": timezone.now() + timedelta(days=1)}
        )


@pytest.fixture()
def seeded_roles():
    """
    Create users and seed claims for smoke validation.

    Returns a dict with admin/reviewer/customer users.
    """
    groups = _ensure_groups()

    admin_user = _create_user(
        username="smoke_admin", email="smoke_admin@example.com", group=groups["admin"]
    )
    reviewer_user = _create_user(
        username="smoke_reviewer", email="smoke_reviewer@example.com", group=groups["reviewer"]
    )
    customer_user = _create_user(
        username="smoke_customer", email="smoke_customer@example.com", group=groups["customer"]
    )

    reviewer_policy = _policy_for_email(
        email="smoke_reviewer_holder@example.com", policy_number="SMOKE-PL-REVIEWER-0001"
    )
    customer_policy = _policy_for_email(
        email=customer_user.email, policy_number="SMOKE-PL-CUSTOMER-0001"
    )

    _seed_claims_for_pagination(
        customer_user=customer_user,
        customer_policy=customer_policy,
        reviewer_policy=reviewer_policy,
        count=16,
    )

    return {"admin": admin_user, "reviewer": reviewer_user, "customer": customer_user}


def _login_via_surface(client, *, login_path: str, username: str) -> None:
    """Log in via the surface entry point."""
    response = client.post(
        login_path, data={"username": username, "password": DEMO_PASSWORD}, follow=False
    )
    assert response.status_code in (302, 303)


def test_admin_smoke_hits_paginated_lists(client, seeded_roles):
    admin_user = seeded_roles["admin"]
    _login_via_surface(client, login_path="/login/admin/", username=admin_user.username)

    assert client.get("/ops/queue/?page=1").status_code == 200
    assert client.get("/ops/queue/?page=2").status_code == 200
    assert client.get("/customer/?page=1").status_code == 200
    assert client.get("/customer/?page=2").status_code == 200


def test_reviewer_smoke_hits_reviewer_queue_pages(client, seeded_roles):
    reviewer_user = seeded_roles["reviewer"]
    _login_via_surface(client, login_path="/login/reviewer/", username=reviewer_user.username)

    assert client.get("/ops/queue/?page=1").status_code == 200
    assert client.get("/ops/queue/?page=2").status_code == 200


def test_customer_smoke_hits_customer_list_pages(client, seeded_roles):
    customer_user = seeded_roles["customer"]
    _login_via_surface(client, login_path="/login/customer/", username=customer_user.username)

    assert client.get("/customer/?page=1").status_code == 200
    assert client.get("/customer/?page=2").status_code == 200
