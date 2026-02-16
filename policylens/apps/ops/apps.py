# path: policylens/apps/ops/apps.py
"""Ops app configuration."""

from django.apps import AppConfig


class OpsConfig(AppConfig):
    """Config for server-rendered ops UI."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ops"
