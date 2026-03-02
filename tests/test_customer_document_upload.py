"""
DB-hitting tests for customer document upload permissions.

Requirements
- Customer can upload documents only to owned claims.
- Upload to non-owned claim is rejected without leaking claim existence.
- Document is persisted against the claim so reviewer surfaces can read it.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

from policylens.apps.claims.models import Claim, Policy, PolicyHolder  # type: ignore
from policylens.apps.customer.views import _resolve_document_model_spec  # type: ignore

pytestmark = pytest.mark.django_db


@pytest.fixture()
def roles():
    return {
        "customer": Group.objects.get_or_create(name="customer")[0],
        "reviewer": Group.objects.get_or_create(name="reviewer")[0],
        "admin": Group.objects.get_or_create(name="admin")[0],
    }


@pytest.fixture()
def users(roles):
    User = get_user_model()

    c1 = User.objects.create_user(
        username="cust_up_1",
        email="cust_up_1@example.com",
        password="pass-12345-strong",
    )
    c1.groups.add(roles["customer"])

    c2 = User.objects.create_user(
        username="cust_up_2",
        email="cust_up_2@example.com",
        password="pass-12345-strong",
    )
    c2.groups.add(roles["customer"])

    reviewer = User.objects.create_user(
        username="rev_up",
        email="rev_up@example.com",
        password="pass-12345-strong",
    )
    reviewer.groups.add(roles["reviewer"])

    admin = User.objects.create_user(
        username="admin_up",
        email="admin_up@example.com",
        password="pass-12345-strong",
    )
    admin.groups.add(roles["admin"])

    return {"c1": c1, "c2": c2, "reviewer": reviewer, "admin": admin}


def _policy_for(email: str) -> Policy:
    holder, _ = PolicyHolder.objects.get_or_create(
        email=email,
        defaults={"full_name": "Upload Customer", "phone": ""},
    )
    policy, _ = Policy.objects.get_or_create(
        policy_number=f"UP-{email}",
        defaults={
            "holder": holder,
            "product_type": "Home Insurance",
            "status": Policy.Status.ACTIVE,
        },
    )
    return policy


def _claim_for(policy: Policy, idx: int, *, created_by: str) -> Claim:
    return Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        status=Claim.Status.NEW,
        priority=Claim.Priority.NORMAL,
        summary=f"Upload claim {idx}",
        created_by=created_by,
    )


def test_customer_can_upload_document_to_owned_claim(client, users):
    spec = _resolve_document_model_spec()

    claim = _claim_for(
        _policy_for("cust_up_1@example.com"),
        idx=1,
        created_by=users["c1"].username,
    )
    client.force_login(users["c1"])

    upload = SimpleUploadedFile("evidence.txt", b"evidence-bytes", content_type="text/plain")
    r = client.post(
        f"/customer/claims/{claim.id}/documents/upload/", data={"file": upload}, follow=False
    )
    assert r.status_code in (302, 303)

    assert spec.model.objects.filter(**{spec.claim_fk_field: claim}).exists()


def test_customer_cannot_upload_document_to_non_owned_claim(client, users):
    claim_other = _claim_for(
        _policy_for("cust_up_2@example.com"),
        idx=2,
        created_by=users["c2"].username,
    )

    client.force_login(users["c1"])
    upload = SimpleUploadedFile("evidence.txt", b"evidence-bytes", content_type="text/plain")
    r = client.post(
        f"/customer/claims/{claim_other.id}/documents/upload/", data={"file": upload}, follow=False
    )

    # 404 avoids leaking whether the claim exists to this user.
    assert r.status_code == 404


def test_admin_customer_view_is_read_only_and_blocks_upload(client, users):
    claim = _claim_for(
        _policy_for("admin_up@example.com"),
        idx=3,
        created_by=users["admin"].username,
    )
    client.force_login(users["admin"])

    detail = client.get(f"/customer/claims/{claim.id}/")
    assert detail.status_code == 200
    assert b"Read-only mode" in detail.content

    upload = SimpleUploadedFile("evidence.txt", b"evidence-bytes", content_type="text/plain")
    blocked = client.post(
        f"/customer/claims/{claim.id}/documents/upload/",
        data={"file": upload},
        follow=False,
    )
    assert blocked.status_code == 403


def test_multi_role_user_logged_via_admin_entry_is_read_only_on_customer_upload(client, roles):
    User = get_user_model()
    user = User.objects.create_user(
        username="multi_role_customer_admin",
        email="multi_role_customer_admin@example.com",
        password="pass-12345-strong",
    )
    user.groups.add(roles["admin"], roles["customer"])

    claim = _claim_for(
        _policy_for("multi_role_customer_admin@example.com"),
        idx=4,
        created_by=user.username,
    )

    login = client.post(
        "/login/admin/",
        data={"username": user.username, "password": "pass-12345-strong"},
        follow=False,
    )
    assert login.status_code == 302

    upload = SimpleUploadedFile("evidence.txt", b"evidence-bytes", content_type="text/plain")
    blocked = client.post(
        f"/customer/claims/{claim.id}/documents/upload/",
        data={"file": upload},
        follow=False,
    )
    assert blocked.status_code == 403
