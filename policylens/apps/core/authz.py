"""
Authorisation helpers for PolicyLens.

This module centralises:
- group name constants
- role checks for console and surface gating

Keeping these checks in one place reduces drift between UI surfaces and
future API endpoints.
"""

from __future__ import annotations

from collections.abc import Iterable

GROUP_ADMIN = "admin"
GROUP_REVIEWER = "reviewer"
GROUP_CUSTOMER = "customer"


def user_in_any_group(user: object, group_names: Iterable[str]) -> bool:
    """
    Return True if the authenticated user belongs to any of the named groups.

    Assumptions:
    - `user` has `is_authenticated` and a Django `groups` related manager.
    """
    if not getattr(user, "is_authenticated", False):
        return False

    # Use group names, not IDs, so behaviour is stable across environments.
    return user.groups.filter(name__in=list(group_names)).exists()


def user_is_admin(user: object) -> bool:
    """
    Return True if the user may access the admin surface.

    Rules:
    - Superusers always allowed.
    - Members of the 'admin' group allowed.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user_in_any_group(user, [GROUP_ADMIN])


def user_is_reviewer(user: object) -> bool:
    """
    Return True if the user may access the reviewer surface.

    Rules:
    - Superusers always allowed.
    - Members of 'reviewer' or 'admin' group allowed.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user_in_any_group(user, [GROUP_REVIEWER, GROUP_ADMIN])


def user_is_customer(user: object) -> bool:
    """
    Return True if the user may access the customer surface.

    Rules:
    - Superusers always allowed.
    - Members of 'customer' or 'admin' group allowed.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user_in_any_group(user, [GROUP_CUSTOMER, GROUP_ADMIN])
