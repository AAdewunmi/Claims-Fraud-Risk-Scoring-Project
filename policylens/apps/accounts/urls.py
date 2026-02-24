"""
URL routes for authentication and surface consoles.
"""

from django.urls import path

from policylens.apps.accounts.views import (
    ConsolePlaceholderView,
    SurfaceLoginView,
    forbidden_view,
)

app_name = "accounts"

urlpatterns = [
    # Surface-specific login entry points (single auth mechanism underneath).
    path("login/admin/", SurfaceLoginView.as_view(surface="admin"), name="login_admin"),
    path("login/reviewer/", SurfaceLoginView.as_view(surface="reviewer"), name="login_reviewer"),
    path("login/customer/", SurfaceLoginView.as_view(surface="customer"), name="login_customer"),
    # Product consoles (placeholders for Day 1 so redirects are deterministic).
    path("console/admin/", ConsolePlaceholderView.as_view(surface="admin"), name="console_admin"),
    path(
        "console/reviewer/",
        ConsolePlaceholderView.as_view(surface="reviewer"),
        name="console_reviewer",
    ),
    path(
        "console/customer/",
        ConsolePlaceholderView.as_view(surface="customer"),
        name="console_customer",
    ),
    # Shared forbidden page (used directly and as a future 403 handler target).
    path("forbidden/", forbidden_view, name="forbidden"),
]
