"""
Console views for PolicyLens.

Each console:
- redirects anonymous users to the correct surface login entry point, with `next`
- returns 403 with a shared forbidden template for authenticated wrong-role access
- renders a role-specific home template when access is allowed
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import TemplateView

from policylens.apps.core.authz import user_is_admin, user_is_customer, user_is_reviewer
from policylens.apps.customer.views import customer_claim_list
from policylens.apps.ops.views import ops_queue


class RoleConsoleView(TemplateView):
    """
    Base console view with deterministic login redirect and role gating.

    Subclasses must set:
    - template_name
    - surface_login_url_name
    - access_check
    """

    template_name: str = ""
    surface_login_url_name: str = ""
    access_check: callable = staticmethod(lambda _user: False)

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Enforce:
        - anonymous redirect to the correct surface login entry point
        - authenticated wrong-role -> 403 with shared forbidden template
        """
        if not request.user.is_authenticated:
            login_url = reverse(self.surface_login_url_name)
            return redirect(f"{login_url}?next={request.path}")

        if not self.access_check(request.user):
            return render(request, "site/forbidden.html", status=403)

        return super().dispatch(request, *args, **kwargs)


class AdminConsoleView(RoleConsoleView):
    """
    Admin console.

    Requirements:
    - user must be admin (or superuser)
    - console links to Django admin and other consoles
    """

    template_name = "console/admin_home.html"
    surface_login_url_name = "accounts:login_admin"
    access_check = staticmethod(user_is_admin)

    def get_context_data(self, **kwargs):
        """
        Provide navigation targets used by the admin console template.
        """
        context = super().get_context_data(**kwargs)
        context["django_admin_url"] = reverse("admin:index")
        context["reviewer_console_url"] = reverse("console:reviewer_home")
        context["customer_console_url"] = reverse("console:customer_home")
        return context


class ReviewerConsoleView(RoleConsoleView):
    """Reviewer console entry point rendering the reviewer dashboard."""

    template_name = "console/reviewer_home.html"
    surface_login_url_name = "accounts:login_reviewer"
    access_check = staticmethod(user_is_reviewer)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Render the reviewer queue dashboard at the console entry path.

        This preserves the stable `/console/reviewer/` entry point while serving
        the real reviewer surface.
        """
        del args, kwargs
        return ops_queue(request)


class CustomerConsoleView(RoleConsoleView):
    """Customer console entry point rendering the customer dashboard."""

    template_name = "console/customer_home.html"
    surface_login_url_name = "accounts:login_customer"
    access_check = staticmethod(user_is_customer)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Render the customer claim list dashboard at the console entry path.

        This preserves the stable `/console/customer/` entry point while serving
        the real customer surface.
        """
        del args, kwargs
        return customer_claim_list(request)
