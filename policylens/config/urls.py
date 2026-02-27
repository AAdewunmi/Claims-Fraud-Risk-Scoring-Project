"""
Root URL configuration for PolicyLens.

This file wires the multi-surface UI:
- public landing
- accounts surface logins
- role consoles
- ops reviewer surface
- customer portal surface
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from policylens.config.views import healthcheck

handler403 = "policylens.apps.accounts.views.forbidden_view"

urlpatterns = [
    path("admin/", admin.site.urls),

    # Public and accounts surfaces
    path("", include("policylens.apps.public.urls")),
    path("", include("policylens.apps.accounts.urls")),

    # Role consoles
    path("", include("policylens.apps.console.urls")),

    # Customer portal
    path("", include("policylens.apps.customer.urls")),

    # API and operational surfaces
    path("api/health/", healthcheck, name="healthcheck"),
    path("api/", include("policylens.apps.claims.api.urls")),
    path("ops/", include("policylens.apps.ops.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
