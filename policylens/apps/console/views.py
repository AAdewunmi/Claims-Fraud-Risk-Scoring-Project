"""
Console views for PolicyLens.

Each console:
- redirects anonymous users to the correct surface login entry point, with `next`
- returns 403 with a shared forbidden template for authenticated wrong-role access
- renders a role-specific home template when access is allowed
"""

from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from policylens.apps.api.views_health import check_database
from policylens.apps.core.authz import user_is_admin, user_is_customer, user_is_reviewer
from policylens.apps.core.models import AdminAuditLog, AdminHealthCheck, AdminOperationalSetting
from policylens.apps.customer.views import customer_claim_list
from policylens.apps.ops.views import ops_queue

ROLE_GROUPS = ("admin", "reviewer", "customer")
ROLE_GROUP_SET = set(ROLE_GROUPS)

ADMIN_OPER_SETTING_SPECS: dict[str, dict[str, object]] = {
    "UI_PAGE_SIZE": {
        "label": "UI page size",
        "value_type": AdminOperationalSetting.ValueType.INTEGER,
        "default": str(getattr(settings, "UI_PAGE_SIZE", 15)),
        "description": "Shared list page size for reviewer and customer surfaces.",
        "min": 5,
        "max": 100,
    },
    "ML_SCORE_THRESHOLD": {
        "label": "ML score threshold",
        "value_type": AdminOperationalSetting.ValueType.FLOAT,
        "default": str(getattr(settings, "ML_SCORE_THRESHOLD", 0.6)),
        "description": "Risk threshold used by ML score interpretation controls.",
        "min": 0.0,
        "max": 1.0,
    },
    "SECURE_SSL_REDIRECT": {
        "label": "Force HTTPS redirect",
        "value_type": AdminOperationalSetting.ValueType.BOOLEAN,
        "default": "true" if bool(getattr(settings, "SECURE_SSL_REDIRECT", False)) else "false",
        "description": "Redirect incoming HTTP traffic to HTTPS.",
    },
}


def _redirect_admin_home(*, notice: str = "", error: str = "") -> HttpResponse:
    """Redirect to admin home and preserve one short status message."""
    params: dict[str, str] = {}
    if notice:
        params["notice"] = notice
    if error:
        params["error"] = error

    url = reverse("console:admin_home")
    if params:
        url = f"{url}?{urlencode(params)}"
    return redirect(url)


def _admin_gate(request: HttpRequest) -> HttpResponse | None:
    """
    Apply admin-surface access rules for function-based admin endpoints.

    - anonymous -> redirect to admin login with next
    - authenticated non-admin -> forbidden template
    """
    if not request.user.is_authenticated:
        login_url = reverse("accounts:login_admin")
        return redirect(f"{login_url}?next={request.path}")

    if not user_is_admin(request.user):
        return render(request, "site/forbidden.html", status=403)

    return None


def _parse_date(raw_value: str) -> date | None:
    """Parse ISO date string (`YYYY-MM-DD`) into a date object."""
    if not raw_value:
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _parse_and_validate_setting_value(key: str, raw_value: str) -> tuple[str | None, str | None]:
    """
    Validate and normalize an operational setting value.

    Returns:
        (normalized_value, error_message)
    """
    spec = ADMIN_OPER_SETTING_SPECS.get(key)
    if spec is None:
        return None, f"Unknown setting key: {key}"

    value_type = spec["value_type"]
    raw = raw_value.strip()

    if value_type == AdminOperationalSetting.ValueType.INTEGER:
        try:
            parsed_int = int(raw)
        except ValueError:
            return None, f"{key} must be an integer."

        min_value = int(spec.get("min", parsed_int))
        max_value = int(spec.get("max", parsed_int))
        if parsed_int < min_value or parsed_int > max_value:
            return None, f"{key} must be between {min_value} and {max_value}."
        return str(parsed_int), None

    if value_type == AdminOperationalSetting.ValueType.FLOAT:
        try:
            parsed_float = float(raw)
        except ValueError:
            return None, f"{key} must be a decimal value."

        min_value = float(spec.get("min", parsed_float))
        max_value = float(spec.get("max", parsed_float))
        if parsed_float < min_value or parsed_float > max_value:
            return None, f"{key} must be between {min_value} and {max_value}."
        return str(parsed_float), None

    if value_type == AdminOperationalSetting.ValueType.BOOLEAN:
        lowered = raw.lower()
        truthy = {"1", "true", "yes", "on"}
        falsy = {"0", "false", "no", "off"}
        if lowered in truthy:
            return "true", None
        if lowered in falsy:
            return "false", None
        return None, f"{key} must be true/false."

    if len(raw) > 255:
        return None, f"{key} exceeds max length (255)."
    return raw, None


def _run_health_check(actor) -> AdminHealthCheck:
    """Execute readiness check and persist a snapshot."""
    db_ok, db_error = check_database()
    details = {"database": {"status": "ok" if db_ok else "error"}}
    if db_error is not None:
        details["database"]["error"] = db_error

    status = "ok" if db_ok else "error"
    health_check = AdminHealthCheck.objects.create(
        status=status,
        details=details,
        checked_by=actor,
    )
    AdminAuditLog.objects.create(
        actor=actor,
        event_type=AdminAuditLog.EventType.HEALTH_CHECKED,
        message="Readiness check executed.",
        metadata={
            "status": status,
            "details": details,
            "checked_at": health_check.checked_at.isoformat(),
        },
    )
    return health_check


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
        Provide navigation and dashboard data used by the admin console template.
        """
        User = get_user_model()
        query = self.request.GET.get("q", "").strip()
        actor_filter = self.request.GET.get("actor", "").strip()
        event_type_filter = self.request.GET.get("event_type", "").strip()
        date_from_raw = self.request.GET.get("date_from", "").strip()
        date_to_raw = self.request.GET.get("date_to", "").strip()

        users_qs = User.objects.all().prefetch_related("groups").order_by("username")
        if query:
            users_qs = users_qs.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
        users = list(users_qs[:100])
        for user in users:
            role_names = sorted(
                [group.name for group in user.groups.all() if group.name in ROLE_GROUP_SET]
            )
            user.role_names = role_names
            user.role_names_display = ", ".join(role_names) if role_names else "none"

        stored_settings = {
            setting.key: setting
            for setting in AdminOperationalSetting.objects.select_related("updated_by").filter(
                key__in=list(ADMIN_OPER_SETTING_SPECS.keys())
            )
        }
        setting_rows = []
        for key, spec in ADMIN_OPER_SETTING_SPECS.items():
            stored = stored_settings.get(key)
            value_type = str(spec["value_type"])
            setting_rows.append(
                {
                    "key": key,
                    "label": str(spec["label"]),
                    "value_type": value_type,
                    "description": str(spec["description"]),
                    "value": stored.value if stored is not None else str(spec["default"]),
                    "updated_at": stored.updated_at if stored is not None else None,
                    "updated_by": stored.updated_by if stored is not None else None,
                }
            )

        audit_qs = AdminAuditLog.objects.select_related("actor", "target_user").all()
        if actor_filter:
            audit_qs = audit_qs.filter(actor__username__icontains=actor_filter)

        valid_event_types = {choice for choice, _ in AdminAuditLog.EventType.choices}
        if event_type_filter in valid_event_types:
            audit_qs = audit_qs.filter(event_type=event_type_filter)

        date_from = _parse_date(date_from_raw)
        date_to = _parse_date(date_to_raw)
        if date_from is not None:
            audit_qs = audit_qs.filter(created_at__date__gte=date_from)
        if date_to is not None:
            audit_qs = audit_qs.filter(created_at__date__lte=date_to)

        latest_health_check = AdminHealthCheck.objects.select_related("checked_by").first()

        context = super().get_context_data(**kwargs)
        context["django_admin_url"] = reverse("admin:index")
        context["reviewer_console_url"] = reverse("console:reviewer_home")
        context["customer_console_url"] = reverse("console:customer_home")
        context["managed_users"] = users
        context["search_query"] = query
        context["setting_rows"] = setting_rows
        context["audit_events"] = list(audit_qs[:100])
        context["event_type_choices"] = AdminAuditLog.EventType.choices
        context["filter_actor"] = actor_filter
        context["filter_event_type"] = event_type_filter
        context["filter_date_from"] = date_from_raw
        context["filter_date_to"] = date_to_raw
        context["latest_health_check"] = latest_health_check
        context["notice"] = self.request.GET.get("notice", "").strip()
        context["error"] = self.request.GET.get("error", "").strip()
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


@require_POST
def admin_update_user(request: HttpRequest, user_id: int) -> HttpResponse:
    """Update role membership and active state for a target user."""
    gate_response = _admin_gate(request)
    if gate_response is not None:
        return gate_response

    User = get_user_model()
    target_user = get_object_or_404(User, pk=user_id)

    requested_roles = [role for role in request.POST.getlist("groups") if role in ROLE_GROUP_SET]
    old_roles = sorted(
        target_user.groups.filter(name__in=ROLE_GROUPS).values_list("name", flat=True)
    )

    role_groups: list[Group] = []
    for role_name in requested_roles:
        group, _ = Group.objects.get_or_create(name=role_name)
        role_groups.append(group)
    target_user.groups.set(role_groups)

    new_roles = sorted(
        target_user.groups.filter(name__in=ROLE_GROUPS).values_list("name", flat=True)
    )
    if old_roles != new_roles:
        AdminAuditLog.objects.create(
            actor=request.user,
            event_type=AdminAuditLog.EventType.USER_ROLE_UPDATED,
            target_user=target_user,
            message=f"Updated role membership for {target_user.username}.",
            metadata={"old_roles": old_roles, "new_roles": new_roles},
        )

    old_is_active = target_user.is_active
    new_is_active = request.POST.get("is_active") == "on"
    if old_is_active != new_is_active:
        target_user.is_active = new_is_active
        target_user.save(update_fields=["is_active"])
        AdminAuditLog.objects.create(
            actor=request.user,
            event_type=AdminAuditLog.EventType.USER_ACCESS_UPDATED,
            target_user=target_user,
            message=f"Updated active access for {target_user.username}.",
            metadata={"old_is_active": old_is_active, "new_is_active": new_is_active},
        )

    return _redirect_admin_home(notice=f"Updated user {target_user.username}.")


@require_POST
def admin_setting_upsert(request: HttpRequest) -> HttpResponse:
    """Validate and upsert a supported operational setting."""
    gate_response = _admin_gate(request)
    if gate_response is not None:
        return gate_response

    key = request.POST.get("key", "").strip().upper()
    raw_value = request.POST.get("value", "").strip()
    spec = ADMIN_OPER_SETTING_SPECS.get(key)
    if spec is None:
        return _redirect_admin_home(error=f"Unsupported setting key: {key}.")

    normalized_value, validation_error = _parse_and_validate_setting_value(key, raw_value)
    if validation_error:
        return _redirect_admin_home(error=validation_error)

    setting, created = AdminOperationalSetting.objects.get_or_create(
        key=key,
        defaults={
            "value": str(normalized_value),
            "value_type": str(spec["value_type"]),
            "description": str(spec["description"]),
            "updated_by": request.user,
        },
    )

    old_value = None if created else setting.value
    setting.value = str(normalized_value)
    setting.value_type = str(spec["value_type"])
    setting.description = str(spec["description"])
    setting.updated_by = request.user
    setting.save()

    AdminAuditLog.objects.create(
        actor=request.user,
        event_type=AdminAuditLog.EventType.CONFIG_UPDATED,
        setting_key=key,
        message=f"Updated operational setting {key}.",
        metadata={
            "created": created,
            "old_value": old_value,
            "new_value": setting.value,
            "value_type": setting.value_type,
        },
    )
    return _redirect_admin_home(notice=f"Updated setting {key}.")


@require_POST
def admin_run_health_check(request: HttpRequest) -> HttpResponse:
    """Run and persist a readiness check from the admin console."""
    gate_response = _admin_gate(request)
    if gate_response is not None:
        return gate_response

    health_check = _run_health_check(request.user)
    return _redirect_admin_home(notice=f"Health check status: {health_check.status}.")


def admin_audit_detail(request: HttpRequest, event_id: int) -> HttpResponse:
    """Render a full detail view for one admin audit event."""
    gate_response = _admin_gate(request)
    if gate_response is not None:
        return gate_response

    event = get_object_or_404(
        AdminAuditLog.objects.select_related("actor", "target_user"),
        pk=event_id,
    )
    return render(
        request,
        "console/admin_audit_detail.html",
        {
            "event": event,
            "django_admin_url": reverse("admin:index"),
            "reviewer_console_url": reverse("console:reviewer_home"),
            "customer_console_url": reverse("console:customer_home"),
        },
    )
