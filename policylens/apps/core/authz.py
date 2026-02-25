"""
Temporary role authorization helpers for console surfaces.

TODO(next issue): Replace with the full authz module implementation.
"""

from __future__ import annotations

GROUP_ADMIN = "admin"
GROUP_REVIEWER = "reviewer"
GROUP_CUSTOMER = "customer"


def _is_authenticated(user) -> bool:
    return bool(getattr(user, "is_authenticated", False))


def _in_any_group(user, group_names: tuple[str, ...]) -> bool:
    return user.groups.filter(name__in=group_names).exists()


def user_is_admin(user) -> bool:
    if not _is_authenticated(user):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _in_any_group(user, (GROUP_ADMIN,))


def user_is_reviewer(user) -> bool:
    if not _is_authenticated(user):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _in_any_group(user, (GROUP_REVIEWER, GROUP_ADMIN))


def user_is_customer(user) -> bool:
    if not _is_authenticated(user):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _in_any_group(user, (GROUP_CUSTOMER, GROUP_ADMIN))
