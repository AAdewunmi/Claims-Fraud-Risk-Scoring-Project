# path: tests/test_ops_app_config.py
"""Tests for ops app configuration."""

from __future__ import annotations

from policylens.apps.ops.apps import OpsConfig


def test_ops_app_config_values():
    """OpsConfig exposes the expected Django app metadata."""
    assert OpsConfig.default_auto_field == "django.db.models.BigAutoField"
    assert OpsConfig.name == "apps.ops"
