"""
Public site surfaces for PolicyLens.

This app owns the unauthenticated landing page and other public-facing pages
that should not route through Django admin login plumbing.
"""

from django.apps import AppConfig


class PublicConfig(AppConfig):
    """Django AppConfig for the public site surfaces."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "policylens.apps.public"
    verbose_name = "Public"
