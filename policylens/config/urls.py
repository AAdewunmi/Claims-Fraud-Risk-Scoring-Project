# path: policylens/config/urls.py
"""Root URL configuration."""

from importlib.util import find_spec

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from policylens.config.views import healthcheck


def _module_exists(module_path: str) -> bool:
    try:
        return find_spec(module_path) is not None
    except ModuleNotFoundError:
        return False


_accounts_available = _module_exists("policylens.apps.accounts.urls")
if _accounts_available:
    handler403 = "policylens.apps.accounts.views.forbidden_view"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("policylens.apps.public.urls")),
    path("api/health/", healthcheck, name="healthcheck"),
    path("api/", include("policylens.apps.claims.api.urls")),
    path("ops/", include("policylens.apps.ops.urls")),
]

# TODO(accounts): remove this guard once account routes are implemented.
if _accounts_available:
    urlpatterns.append(path("", include("policylens.apps.accounts.urls")))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
