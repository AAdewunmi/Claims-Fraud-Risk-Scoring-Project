"""
Views for authentication and surface consoles.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import FormView

SURFACE_INTENT_SESSION_KEY = "policylens_surface_intent"


@dataclass(frozen=True)
class SurfaceSpec:
    """Configuration for a product surface."""

    surface: str
    title: str
    console_url_name: str


SURFACES: dict[str, SurfaceSpec] = {
    "admin": SurfaceSpec(
        surface="admin", title="Admin login", console_url_name="accounts:console_admin"
    ),
    "reviewer": SurfaceSpec(
        surface="reviewer", title="Reviewer login", console_url_name="accounts:console_reviewer"
    ),
    "customer": SurfaceSpec(
        surface="customer", title="Customer login", console_url_name="accounts:console_customer"
    ),
}


class SurfaceLoginView(FormView):
    """
    Surface-specific login view that uses Django's AuthenticationForm.

    The key behaviour is that the surface intent is captured and preserved in
    the session so later routing and gating can respond deterministically.
    """

    template_name = "accounts/login_surface.html"
    form_class = AuthenticationForm

    # Set by as_view(surface="...") in urls.py
    surface: str | None = None

    @classmethod
    def as_view(cls, **initkwargs):
        """
        Add a small guard: only allow known surfaces.

        This avoids silent misconfiguration if a URL is wired incorrectly.
        """
        surface = initkwargs.get("surface")
        if surface not in SURFACES:
            raise ValueError(
                f"Unknown surface '{surface}'. Expected one of: {', '.join(SURFACES.keys())}"
            )
        return super().as_view(**initkwargs)

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Store surface intent early so even GET requests establish user intent.
        """
        assert self.surface is not None
        request.session[SURFACE_INTENT_SESSION_KEY] = self.surface
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        AuthenticationForm requires the request in form kwargs.
        """
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Provide surface metadata for template rendering.
        """
        context = super().get_context_data(**kwargs)
        assert self.surface is not None
        spec = SURFACES[self.surface]
        context["surface"] = spec.surface
        context["surface_title"] = spec.title
        return context

    def form_valid(self, form: AuthenticationForm) -> HttpResponse:
        """
        Log the user in and redirect to the surface console.
        """
        user = form.get_user()
        if user is None:
            # AuthenticationForm should not reach here without a user, but keep it explicit.
            return HttpResponseBadRequest("Login failed.")
        login(self.request, user)
        return redirect(self.get_success_url())

    def get_success_url(self) -> str:
        """
        Surface-specific redirect intent.

        Day 1 uses placeholder consoles so the redirect target exists and can be tested.
        """
        assert self.surface is not None
        spec = SURFACES[self.surface]
        return reverse(spec.console_url_name)


@method_decorator(require_http_methods(["GET"]), name="dispatch")
class ConsolePlaceholderView(View):
    """
    Placeholder console pages for Day 1.

    These exist so surface login redirects are deterministic and testable.
    Later sprints will replace these with real dashboards and role-gating.
    """

    surface: str | None = None

    @classmethod
    def as_view(cls, **initkwargs):
        surface = initkwargs.get("surface")
        if surface not in SURFACES:
            raise ValueError(
                f"Unknown surface '{surface}'. Expected one of: {', '.join(SURFACES.keys())}"
            )
        return super().as_view(**initkwargs)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        assert self.surface is not None
        spec = SURFACES[self.surface]

        # Simple, dependency-free placeholder response.
        # We do not enforce auth here on Day 1; boundary tests and gating land in later days.
        html = (
            "<!doctype html>"
            "<html><head><meta charset='utf-8'><title>Console</title></head>"
            "<body style='font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;'>"
            f"<h1>{spec.surface.capitalize()} console</h1>"
            "<p>This is a Day 1 placeholder so surface login redirects are deterministic.</p>"
            "<p>Replace this with real dashboards and access checks in subsequent days.</p>"
            "<p><a href='/'>Back to landing</a></p>"
            "</body></html>"
        )
        return HttpResponse(html)


@require_http_methods(["GET"])
def forbidden_view(request: HttpRequest) -> HttpResponse:
    """
    Shared forbidden page.

    This is used directly at /forbidden/ and can also be wired as handler403 so
    wrong-role access renders a consistent template.
    """
    return render(request, "site/forbidden.html", status=403)
