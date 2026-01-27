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
]
