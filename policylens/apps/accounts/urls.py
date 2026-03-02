"""
URL routes for authentication and shared access pages.
"""

from django.urls import path

from policylens.apps.accounts.views import (
    SurfaceLoginView,
    forbidden_view,
    logout_to_landing,
)

app_name = "accounts"

urlpatterns = [
    # Surface-specific login entry points (single auth mechanism underneath).
    path("login/admin/", SurfaceLoginView.as_view(surface="admin"), name="login_admin"),
    path("login/reviewer/", SurfaceLoginView.as_view(surface="reviewer"), name="login_reviewer"),
    path("login/customer/", SurfaceLoginView.as_view(surface="customer"), name="login_customer"),
    path("logout/", logout_to_landing, name="logout_to_landing"),
    # Shared forbidden page (used directly and as a future 403 handler target).
    path("forbidden/", forbidden_view, name="forbidden"),
]
