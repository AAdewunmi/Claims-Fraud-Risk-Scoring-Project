"""
URL routes for console surfaces.
"""

from django.urls import path

from policylens.apps.console.views import (
    AdminConsoleView,
    CustomerConsoleView,
    ReviewerConsoleView,
    admin_audit_detail,
    admin_run_health_check,
    admin_setting_upsert,
    admin_update_user,
)

app_name = "console"

urlpatterns = [
    path("console/admin/", AdminConsoleView.as_view(), name="admin_home"),
    path("console/admin/users/<int:user_id>/", admin_update_user, name="admin_user_update"),
    path("console/admin/settings/upsert/", admin_setting_upsert, name="admin_setting_upsert"),
    path("console/admin/health/run/", admin_run_health_check, name="admin_health_run"),
    path("console/admin/audit/<int:event_id>/", admin_audit_detail, name="admin_audit_detail"),
    path("console/reviewer/", ReviewerConsoleView.as_view(), name="reviewer_home"),
    path("console/customer/", CustomerConsoleView.as_view(), name="customer_home"),
]
