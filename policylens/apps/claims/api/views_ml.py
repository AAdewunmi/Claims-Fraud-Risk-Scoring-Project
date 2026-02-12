# path: policylens/apps/claims/api/views_ml.py
"""ML scoring API views."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from policylens.apps.claims.api.permissions import IsReviewerOrAdmin
from policylens.apps.claims.api.serializers_ml import MlScoreSerializer
from policylens.apps.claims.ml.scoring import ModelNotReady, score_claim
from policylens.apps.claims.models import Claim


def _actor_from_request(request) -> str:
    """Return a stable actor id for audit events."""
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return user.get_username() or str(user.pk)
    return "anonymous"


class ClaimMlScoreAPIView(APIView):
    """Score a claim and return the persisted MlScore.

    Contract:
    - POST /api/claims/{id}/ml-score/
    """

    permission_classes = [IsAuthenticated, IsReviewerOrAdmin]

    def post(self, request, claim_id: int):
        """Score claim, persist MlScore, return ML contract."""
        claim = get_object_or_404(Claim, pk=claim_id)
        actor = _actor_from_request(request)

        try:
            ml = score_claim(claim=claim, actor=actor)
        except ModelNotReady as exc:
            return Response({"detail": f"Model not ready: {exc}"}, status=503)

        return Response(MlScoreSerializer(ml).data, status=200)
