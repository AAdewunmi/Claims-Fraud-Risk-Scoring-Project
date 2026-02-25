"""
Role consoles for PolicyLens.

Consoles are the first authenticated footholds inside the product UI.
They exist to make post-login routing deterministic and to anchor role-based
navigation away from Django admin as the default experience.
"""

from django.apps import AppConfig


class ConsoleConfig(AppConfig):
    """Django AppConfig for the PolicyLens console surfaces."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "policylens.apps.console"
    verbose_name = "Console"
