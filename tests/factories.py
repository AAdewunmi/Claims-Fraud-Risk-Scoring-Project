# path: policylens/tests/factories.py
"""
Factories for deterministic test data.

Factories target the domain models, not DRF serializers, so that tests can focus on
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