# path: policylens/apps/ops/views.py
"""
Ops views (server-rendered).

Week 5 begins with the UI shell and queue placeholder.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


@login_required
def ops_home(request: HttpRequest) -> HttpResponse:
    """Redirect ops landing to queue."""
    return redirect("ops:queue")


@login_required
def queue_view(request: HttpRequest) -> HttpResponse:
    """Render queue shell. Data wiring lands Tuesday."""
    return render(request, "ops/queue.html", context={"page_title": "Review queue"})
