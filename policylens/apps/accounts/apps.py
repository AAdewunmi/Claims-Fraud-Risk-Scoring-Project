"""
Accounts and authentication surfaces for PolicyLens.

This app provides surface-specific login entry points that share the same
authentication backend, while preserving the user's intent about which surface
they are trying to access.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Django AppConfig for accounts and auth surfaces."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "policylens.apps.accounts"
    verbose_name = "Accounts"
