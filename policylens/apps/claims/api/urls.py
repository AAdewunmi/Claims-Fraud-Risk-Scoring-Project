# path: policylens/apps/claims/api/urls.py
"""Claims API routes."""

from django.urls import path

from policylens.apps.claims.api.views import (
    ClaimDecisionCreateAPIView,
    ClaimDocumentUploadAPIView,
    ClaimListCreateAPIView,
    ClaimNoteCreateAPIView,
    ClaimRetrieveAPIView,
)
from policylens.apps.claims.api.views_audit import ClaimAuditEventListAPIView
from policylens.apps.claims.api.views_export import ClaimAuditExportAPIView
from policylens.apps.claims.api.views_ml import ClaimMlScoreAPIView
from policylens.apps.claims.api.views_queue import QueueClaimListAPIView

urlpatterns = [
    path("claims/", ClaimListCreateAPIView.as_view(), name="claims-list-create"),
    path("claims/<int:claim_id>/", ClaimRetrieveAPIView.as_view(), name="claims-retrieve"),
    path(
        "claims/<int:claim_id>/documents/",
        ClaimDocumentUploadAPIView.as_view(),
        name="claims-documents-create",
    ),
    path(
        "claims/<int:claim_id>/notes/",
        ClaimNoteCreateAPIView.as_view(),
        name="claims-notes-create",
    ),
    path(
        "claims/<int:claim_id>/decisions/",
        ClaimDecisionCreateAPIView.as_view(),
        name="claims-decisions-create",
    ),
    path(
        "claims/<int:claim_id>/audit-events/",
        ClaimAuditEventListAPIView.as_view(),
        name="claims-audit-events",
    ),
    path(
        "claims/<int:claim_id>/audit-export/",
        ClaimAuditExportAPIView.as_view(),
        name="claims-audit-export",
    ),
    path(
        "claims/<int:claim_id>/ml-score/",
        ClaimMlScoreAPIView.as_view(),
        name="claims-ml-score",
    ),
    path("queue/claims/", QueueClaimListAPIView.as_view(), name="queue-claims"),
]
