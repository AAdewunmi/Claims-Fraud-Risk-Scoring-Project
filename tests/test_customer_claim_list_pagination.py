"""
DB-hitting tests for customer claim list one-claim contract.

Contract
- Customer list surfaces only one claim, even if multiple owned claims exist.
- Page values outside range resolve to the single available page.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from policylens.apps.claims.models import Claim, Policy, PolicyHolder  # type: ignore

pytestmark = pytest.mark.django_db


@pytest.fixture()
def customer_user():
    User = get_user_model()
    group = Group.objects.get_or_create(name="customer")[0]
    user = User.objects.create_user(
        username="cust_pager",
        email="cust_pager@example.com",
        password="pass-12345-strong",
    )
    user.groups.add(group)
    return user


@pytest.fixture()
def customer_claims(customer_user):
    holder, _ = PolicyHolder.objects.get_or_create(
        email="cust_pager@example.com",
        defaults={"full_name": "Customer Pager", "phone": ""},
    )
    policy, _ = Policy.objects.get_or_create(
        policy_number="CUST-PAGER-0001",
        defaults={
            "holder": holder,
            "product_type": "Home Insurance",
            "status": Policy.Status.ACTIVE,
        },
    )

    created = []
    for i in range(40):
        created.append(
            Claim.objects.create(
                policy=policy,
                claim_type=Claim.Type.CLAIM,
                status=Claim.Status.NEW,
                priority=Claim.Priority.NORMAL,
                summary=f"Paged claim {i}",
                created_by=customer_user.username,
            )
        )
    return created


def test_customer_list_is_limited_to_one_claim(client, customer_user, customer_claims):
    client.force_login(customer_user)

    r = client.get("/customer/?page=1")
    assert r.status_code == 200
    p = r.context["pagination"]
    items = list(r.context["claims"])

    assert p.total_count == 1
    assert p.showing_from == 1
    assert p.showing_to == 1
    assert len(items) == 1

    expected_primary = (
        Claim.objects.filter(created_by=customer_user.username).order_by("-created_at", "id").first()
    )
    assert expected_primary is not None
    assert items[0].id == expected_primary.id


def test_customer_page_two_resolves_to_single_page(client, customer_user, customer_claims):
    client.force_login(customer_user)

    r = client.get("/customer/?page=2")
    assert r.status_code == 200
    p = r.context["pagination"]

    assert p.total_count == 1
    assert p.page_obj.number == 1
