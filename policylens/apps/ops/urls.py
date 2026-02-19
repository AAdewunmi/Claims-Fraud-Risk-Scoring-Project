# path: policylens/apps/ops/urls.py
"""URL routes for the ops UI."""

from django.urls import path

from policylens.apps.ops.views import claim_detail_view, ops_home, queue_view
from policylens.apps.ops.views_htmx import htmx_add_note, htmx_score_claim

app_name = "ops"

urlpatterns = [
    path("", ops_home, name="home"),
    path("queue/", queue_view, name="queue"),
    path("claims/<int:claim_id>/", claim_detail_view, name="claim-detail"),
    # HTMX endpoints
    path("claims/<int:claim_id>/htmx/notes/add/", htmx_add_note, name="htmx-add-note"),
    path("claims/<int:claim_id>/htmx/ml-score/", htmx_score_claim, name="htmx-score-claim"),
]
