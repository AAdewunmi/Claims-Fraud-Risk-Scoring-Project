# path: policylens/apps/claims/api/permissions.py
"""
API permission classes for PolicyLens claims endpoints.

Role model:
- Staff or superuser is always allowed.
- A user in the "reviewer" group is allowed.
- A user in the "admin" group is allowed (optional group, not required if you use staff).

These permissions are intentionally simple and deterministic to keep API behaviour stable.
"""

from __future__ import annotations

from typing import AbstractSet

from rest_framework.permissions import BasePermission


def _user_group_names(user) -> AbstractSet[str]:
    """Return the set of Django auth group names for a user.

    Args:
        user: Django User instance.

    Returns:
        A set of group name strings. Empty set for anonymous users.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    return set(user.groups.values_list("name", flat=True))


class IsReviewerOrAdmin(BasePermission):
    """Allow access only to reviewer or admin roles (or staff/superuser).

    This is used to gate endpoints that can mutate workflow state or produce evidence,
    such as decision writes and ML scoring triggers.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view) -> bool:
        """Return True if the request should be permitted."""
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return False

        # Staff/superuser always allowed as the operational override.
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            return True

        groups = _user_group_names(user)
        return "reviewer" in groups or "admin" in groups
