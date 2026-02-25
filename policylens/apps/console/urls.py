"""
URL routes for console surfaces.
"""

from django.urls import path

from policylens.apps.console.views import (
    AdminConsoleView,
    CustomerConsoleView,
    ReviewerConsoleView,
)

app_name = "console"

urlpatterns = [
    path("console/admin/", AdminConsoleView.as_view(), name="admin_home"),
    path("console/reviewer/", ReviewerConsoleView.as_view(), name="reviewer_home"),
    path("console/customer/", CustomerConsoleView.as_view(), name="customer_home"),
]
