# path: policylens/apps/claims/apps.py
"""Django app configuration for the claims domain."""

from django.apps import AppConfig


class ClaimsConfig(AppConfig):
    """Config for the claims app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.claims"
