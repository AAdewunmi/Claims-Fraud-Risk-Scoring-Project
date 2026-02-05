# path: policylens/apps/core/apps.py
"""Core application configuration."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Config for core app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
