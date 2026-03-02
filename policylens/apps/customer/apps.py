"""
Customer console surfaces for PolicyLens.

This app provides the authenticated customer-facing console:
- claim list scoped to ownership
- claim detail scoped to ownership
- document upload restricted to owned claims
"""

from django.apps import AppConfig


class CustomerConfig(AppConfig):
    """Django AppConfig for customer console surfaces."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "policylens.apps.customer"
    verbose_name = "Customer"
