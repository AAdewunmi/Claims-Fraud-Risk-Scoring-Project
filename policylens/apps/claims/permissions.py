# path: policylens/apps/claims/api/permissions.py
"""
API permission classes for PolicyLens roles.

Week 2 introduces two roles:
- reviewer: can action claims (decisions, notes, documents)
- admin: can do everything reviewers can, plus future administrative actions

Roles are backed by Django Groups for simplicity and auditability.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission

ROLE_REVIEWER = "reviewer"
ROLE_ADMIN = "admin"


def user_in_group(user, group_name: str) -> bool:
    """Return True if an authenticated user is in the given group."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name=group_name).exists()


class IsReviewerOrAdmin(BasePermission):
    """Allow access only to reviewer or admin roles."""

    message = "Reviewer or admin role required."

    def has_permission(self, request, view) -> bool:
        """Check group membership."""
        user = getattr(request, "user", None)
        return user_in_group(user, ROLE_REVIEWER) or user_in_group(user, ROLE_ADMIN)
