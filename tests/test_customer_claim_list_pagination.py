"""
DB-hitting tests for customer claim list pagination contract.

Contract
- page param is 1-indexed
- page size is 15
- invalid/negative page -> page 1
- out of range -> last page
- links preserve query params
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


def test_page_size_is_15(client, customer_user, customer_claims):
    client.force_login(customer_user)

    r = client.get("/customer/?page=1")
    assert r.status_code == 200
    p = r.context["pagination"]
    assert p.paginator.per_page == 15
    assert p.total_count == 40
    assert p.showing_from == 1
    assert p.showing_to == 15


def test_invalid_page_falls_back_to_page_1(client, customer_user, customer_claims):
    client.force_login(customer_user)

    r = client.get("/customer/?page=banana")
    assert r.status_code == 200
    p = r.context["pagination"]
    assert p.page_obj.number == 1


def test_negative_page_falls_back_to_page_1(client, customer_user, customer_claims):
    client.force_login(customer_user)

    r = client.get("/customer/?page=-1")
    assert r.status_code == 200
    p = r.context["pagination"]
    assert p.page_obj.number == 1


def test_out_of_range_page_returns_last_page(client, customer_user, customer_claims):
    client.force_login(customer_user)

    r = client.get("/customer/?page=999999")
    assert r.status_code == 200
    p = r.context["pagination"]
    assert p.page_obj.number == p.paginator.num_pages


def test_links_preserve_query_params(client, customer_user, customer_claims):
    client.force_login(customer_user)

    r = client.get("/customer/?status=NEW&foo=bar&page=2")
    assert r.status_code == 200
    p = r.context["pagination"]

    urls = [p.first_url, p.prev_url, p.next_url, p.last_url] + [link.url for link in p.page_links]
    urls = [u for u in urls if u]
    assert urls, "Expected at least one pagination URL."
    assert all("foo=bar" in u for u in urls)
    assert all("status=NEW" in u for u in urls)
