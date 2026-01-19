# path: policylens/config/views.py
"""
Project-level views.

Week 1 includes a minimal healthcheck to validate container boot and routing.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def healthcheck(request):
    """Return a minimal health response for load balancers and smoke tests."""
    return JsonResponse({"status": "ok"})
