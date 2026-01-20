# path: policylens/apps/claims/api/urls.py
"""Claims API routes."""

from django.urls import path

from policylens.apps.claims.api.views import ClaimListCreateAPIView

urlpatterns = [
    path("claims/",
         ClaimListCreateAPIView.as_view(),
         name="claims-list-create"),
]
