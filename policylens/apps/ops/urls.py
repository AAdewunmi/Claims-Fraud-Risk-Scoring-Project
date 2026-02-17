# path: policylens/apps/ops/urls.py
"""URL routes for the ops UI."""

from django.urls import path

from policylens.apps.ops.views import claim_detail_view, ops_home, queue_view

app_name = "ops"

urlpatterns = [
    path("", ops_home, name="home"),
    path("queue/", queue_view, name="queue"),
    path("claims/<int:claim_id>/", claim_detail_view, name="claim-detail"),
]
