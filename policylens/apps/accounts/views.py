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
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import FormView

SURFACE_INTENT_SESSION_KEY = "policylens_surface_intent"

GROUP_REVIEWER = "reviewer"
GROUP_ADMIN = "admin"


@dataclass(frozen=True)
class SurfaceSpec:
    """Configuration for a product surface."""
    surface: str
    title: str
    console_url_name: str


SURFACES: dict[str, SurfaceSpec] = {
    "admin": SurfaceSpec(surface="admin", title="Admin login", console_url_name="accounts:console_admin"),
    "reviewer": SurfaceSpec(surface="reviewer", title="Reviewer login", console_url_name="accounts:console_reviewer"),
    "customer": SurfaceSpec(surface="customer", title="Customer login", console_url_name="accounts:console_customer"),
}


def user_has_reviewer_surface_access(user) -> bool:
    """
    Determine whether a user may access the reviewer surface.

    Rules:
    - Superusers always allowed.
    - Membership of 'reviewer' or 'admin' group allowed.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True

    # Use group names, not IDs, to keep the contract stable across environments.
    return user.groups.filter(name__in=[GROUP_REVIEWER, GROUP_ADMIN]).exists()


class SurfaceLoginView(FormView):
    """
    Surface-specific login view that uses Django's AuthenticationForm.

    This view stores the surface intent and supports an optional `next` URL
    to return the user to the page that triggered the login.
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
            raise ValueError(f"Unknown surface '{surface}'. Expected one of: {', '.join(SURFACES.keys())}")
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

        Also provide the safe `next` value so the template can include it as a hidden field.
        """
        context = super().get_context_data(**kwargs)
        assert self.surface is not None
        spec = SURFACES[self.surface]
        context["surface"] = spec.surface
        context["surface_title"] = spec.title

        # Keep next purely as a local path to avoid open redirects.
        next_candidate = self.request.GET.get("next", "")
        if next_candidate and url_has_allowed_host_and_scheme(
            url=next_candidate,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            context["next"] = next_candidate
        else:
            context["next"] = ""

        return context

    def form_valid(self, form: AuthenticationForm) -> HttpResponse:
        """
        Log the user in and redirect to the `next` URL if present and safe,
        otherwise redirect to the surface console.
        """
        user = form.get_user()
        if user is None:
            return HttpResponseBadRequest("Login failed.")
        login(self.request, user)
        return redirect(self.get_success_url())

    def get_success_url(self) -> str:
        """
        Surface-specific redirect intent with `next` support.

        The `next` value must be a safe local URL to prevent open redirects.
        """
        next_candidate = self.request.POST.get("next") or self.request.GET.get("next")
        if next_candidate and url_has_allowed_host_and_scheme(
            url=next_candidate,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_candidate

        assert self.surface is not None
        spec = SURFACES[self.surface]
        return reverse(spec.console_url_name)


@method_decorator(require_http_methods(["GET"]), name="dispatch")
class ConsolePlaceholderView(View):
    """
    Placeholder console pages for Day 1.

    Reviewer console is the first boundary:
    - anonymous users are redirected to the reviewer login entry point with `next`
    - authenticated users without role access receive a 403 with the shared forbidden template
    """

    surface: str | None = None

    @classmethod
    def as_view(cls, **initkwargs):
        surface = initkwargs.get("surface")
        if surface not in SURFACES:
            raise ValueError(f"Unknown surface '{surface}'. Expected one of: {', '.join(SURFACES.keys())}")
        return super().as_view(**initkwargs)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        assert self.surface is not None
        spec = SURFACES[self.surface]

        if spec.surface == "reviewer":
            if not request.user.is_authenticated:
                login_url = reverse("accounts:login_reviewer")
                return redirect(f"{login_url}?next={reverse('accounts:console_reviewer')}")

            if not user_has_reviewer_surface_access(request.user):
                return render(request, "site/forbidden.html", status=403)

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
