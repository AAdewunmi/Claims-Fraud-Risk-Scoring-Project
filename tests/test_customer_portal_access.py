"""
DB-hitting tests for customer console access and ownership scoping.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from policylens.apps.claims.models import Claim, Policy, PolicyHolder  # type: ignore

pytestmark = pytest.mark.django_db


@pytest.fixture()
def customer_group():
    return Group.objects.get_or_create(name="customer")[0]


@pytest.fixture()
def reviewer_group():
    return Group.objects.get_or_create(name="reviewer")[0]


@pytest.fixture()
def users(customer_group, reviewer_group):
    User = get_user_model()

    c1 = User.objects.create_user(
        username="cust1",
        email="cust1@example.com",
        password="pass-12345-strong",
    )
    c1.groups.add(customer_group)

    c2 = User.objects.create_user(
        username="cust2",
        email="cust2@example.com",
        password="pass-12345-strong",
    )
    c2.groups.add(customer_group)

    reviewer = User.objects.create_user(
        username="rev",
        email="rev@example.com",
        password="pass-12345-strong",
    )
    reviewer.groups.add(reviewer_group)

    return {"c1": c1, "c2": c2, "reviewer": reviewer}


def _make_policy_for_email(email: str) -> Policy:
    holder, _ = PolicyHolder.objects.get_or_create(
        email=email,
        defaults={"full_name": "Customer User", "phone": ""},
    )
    policy, _ = Policy.objects.get_or_create(
        policy_number=f"PL-{email}",
        defaults={
            "holder": holder,
            "product_type": "Home Insurance",
            "status": Policy.Status.ACTIVE,
        },
    )
    return policy


def _make_claim_for_policy(policy: Policy, *, idx: int, created_by: str) -> Claim:
    return Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        status=Claim.Status.NEW,
        priority=Claim.Priority.NORMAL,
        summary=f"Customer claim {idx}",
        created_by=created_by,
    )


def test_customer_console_requires_customer_role(client, users):
    client.force_login(users["reviewer"])
    r = client.get("/customer/")
    assert r.status_code == 403
    assert b"Forbidden" in r.content


def test_customer_only_sees_owned_claims_in_list(client, users):
    policy1 = _make_policy_for_email("cust1@example.com")
    policy2 = _make_policy_for_email("cust2@example.com")

    _make_claim_for_policy(policy1, idx=1, created_by=users["c1"].username)
    _make_claim_for_policy(policy2, idx=2, created_by=users["c2"].username)

    client.force_login(users["c1"])
    r = client.get("/customer/")
    assert r.status_code == 200

    pagination = r.context["pagination"]
    assert pagination.total_count == 1


def test_customer_cannot_open_other_users_claim_detail(client, users):
    policy1 = _make_policy_for_email("cust1@example.com")
    policy2 = _make_policy_for_email("cust2@example.com")

    claim1 = _make_claim_for_policy(policy1, idx=1, created_by=users["c1"].username)
    claim2 = _make_claim_for_policy(policy2, idx=2, created_by=users["c2"].username)

    client.force_login(users["c1"])
    ok = client.get(f"/customer/claims/{claim1.id}/")
    assert ok.status_code == 200

    not_owned = client.get(f"/customer/claims/{claim2.id}/")
    assert not_owned.status_code == 404


def test_customer_cannot_open_second_owned_claim_when_multiple_exist(client, users):
    policy1 = _make_policy_for_email("cust1@example.com")

    first = _make_claim_for_policy(policy1, idx=1, created_by=users["c1"].username)
    second = _make_claim_for_policy(policy1, idx=2, created_by=users["c1"].username)

    primary = (
        Claim.objects.filter(policy=policy1, created_by=users["c1"].username)
        .order_by("-created_at", "id")
        .first()
    )
    assert primary is not None

    client.force_login(users["c1"])
    allowed = client.get(f"/customer/claims/{primary.id}/")
    assert allowed.status_code == 200

    secondary_id = first.id if primary.id == second.id else second.id
    blocked = client.get(f"/customer/claims/{secondary_id}/")
    assert blocked.status_code == 404
