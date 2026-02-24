"""Coverage tests for temporary optional accounts wiring."""

from __future__ import annotations

import importlib
import sys
import types
from importlib import util
from unittest.mock import patch


def _fake_accounts_modules():
    accounts_pkg = types.ModuleType("policylens.apps.accounts")
    accounts_pkg.__path__ = []

    accounts_urls = types.ModuleType("policylens.apps.accounts.urls")
    accounts_urls.app_name = "accounts"
    accounts_urls.urlpatterns = []

    accounts_views = types.ModuleType("policylens.apps.accounts.views")
    accounts_views.forbidden_view = lambda request, exception=None: None

    return {
        "policylens.apps.accounts": accounts_pkg,
        "policylens.apps.accounts.urls": accounts_urls,
        "policylens.apps.accounts.views": accounts_views,
    }


def test_settings_adds_accounts_app_when_module_exists(monkeypatch):
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///db.sqlite3")

    original_find_spec = util.find_spec

    def fake_find_spec(name, package=None):
        if name in {
            "policylens.apps.accounts",
            "policylens.apps.accounts.urls",
            "policylens.apps.accounts.views",
        }:
            return object()
        return original_find_spec(name, package)

    with patch.dict(sys.modules, _fake_accounts_modules(), clear=False):
        with patch("importlib.util.find_spec", side_effect=fake_find_spec):
            settings_module = importlib.import_module("policylens.config.settings")
            reloaded = importlib.reload(settings_module)
            assert "policylens.apps.accounts" in reloaded.INSTALLED_APPS


def test_urls_add_accounts_handler_and_include_when_module_exists():
    original_find_spec = util.find_spec

    def fake_find_spec(name, package=None):
        if name in {
            "policylens.apps.accounts",
            "policylens.apps.accounts.urls",
            "policylens.apps.accounts.views",
        }:
            return object()
        return original_find_spec(name, package)

    with patch.dict(sys.modules, _fake_accounts_modules(), clear=False):
        with patch("importlib.util.find_spec", side_effect=fake_find_spec):
            urls_module = importlib.import_module("policylens.config.urls")
            reloaded = importlib.reload(urls_module)
            assert reloaded.handler403 == "policylens.apps.accounts.views.forbidden_view"
            assert any(
                getattr(getattr(pattern, "urlconf_name", None), "__name__", "")
                == "policylens.apps.accounts.urls"
                for pattern in reloaded.urlpatterns
            )
