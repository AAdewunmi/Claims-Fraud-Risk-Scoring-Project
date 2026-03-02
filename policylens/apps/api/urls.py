# path: policylens/apps/api/urls.py
"""
Top-level API URL routing for PolicyLens.

Contract:
- `/api/health/` is a readiness probe endpoint for infrastructure checks.
- Claims API routes are included at `/api/` to keep domain URLs stable.
"""

from __future__ import annotations

from django.urls import include, path

from policylens.apps.api.views_health import ReadinessHealthAPIView

urlpatterns = [
    path("health/", ReadinessHealthAPIView.as_view(), name="healthcheck"),
    # Mount claims domain API routes under the same `/api/` prefix.
    path("", include("policylens.apps.claims.api.urls")),
]
