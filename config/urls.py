# path: policylens/config/urls.py
"""Root URL configuration for PolicyLens."""

from django.contrib import admin
from django.urls import include, path

from config.views import healthcheck

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", healthcheck, name="healthcheck"),
    path("api/", include("apps.claims.api.urls")),
]
