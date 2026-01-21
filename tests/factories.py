# path: policylens/tests/factories.py
"""
Factories for deterministic test data.

Factories target the domain models, not DRF serializers,
so that tests can focus on
boundary behaviour and service-layer rules.
"""

from __future__ import annotations

import factory
from factory import Faker

from apps.claims.models import Claim, Policy, PolicyHolder


class PolicyHolderFactory(factory.django.DjangoModelFactory):
    """Factory for PolicyHolder."""

    class Meta:
        model = PolicyHolder

    full_name = Faker("name")
    email = Faker("email")
    phone = Faker("phone_number")


class PolicyFactory(factory.django.DjangoModelFactory):
    """Factory for Policy."""

    class Meta:
        model = Policy

    holder = factory.SubFactory(PolicyHolderFactory)
    policy_number = factory.Sequence(lambda n: f"PL-{n:04d}")
    product_type = "Home Insurance"
    status = Policy.Status.ACTIVE


class ClaimFactory(factory.django.DjangoModelFactory):
    """Factory for Claim."""

    class Meta:
        model = Claim

    policy = factory.SubFactory(PolicyFactory)
    claim_type = Claim.Type.CLAIM
    status = Claim.Status.NEW
    priority = Claim.Priority.NORMAL
    summary = Faker("sentence")
    created_by = "test-actor"
