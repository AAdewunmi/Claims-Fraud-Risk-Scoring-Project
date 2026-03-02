# path: policylens/apps/api/views_health.py
"""
Readiness health endpoint for PolicyLens.

This endpoint is intended for load balancers and orchestration readiness checks.
It verifies database connectivity and returns a structured JSON response.

Contract
- GET /api/health/
- 200 when ready
- 503 when not ready
- JSON body always includes:
  - status: "ok" | "error"
  - checks.database.status: "ok" | "error"
  - checks.database.error (only when database check fails)
"""

from __future__ import annotations

from django.db import connections
from django.db.utils import OperationalError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from rest_framework.views import APIView


def check_database() -> tuple[bool, str | None]:
    """
    Verify that the default database connection is usable.

    Returns:
        (ok, error_code)
        - ok is True when a simple SELECT succeeds and returns the expected value.
        - error_code is a stable string identifier suitable for a readiness response.
    """
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()

        # Defensive check: a successful query should return a single row [1].
        if not row or row[0] != 1:
            return False, "UnexpectedSelectResult"

        return True, None
    except OperationalError:
        # Keep the response stable and avoid leaking DB details.
        return False, "OperationalError"
    except Exception as exc:  # noqa: BLE001
        # Catch-all for unexpected failures, still keeping a stable identifier.
        return False, exc.__class__.__name__


class ReadinessHealthAPIView(APIView):
    """
    Readiness endpoint that verifies DB connectivity.

    Authentication is disabled explicitly because this endpoint is commonly used by
    infrastructure components that cannot present credentials.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs) -> Response:
        """
        Return readiness status and check results.

        Response codes:
            200 when all checks pass
            503 when any check fails
        """
        db_ok, db_error = check_database()

        checks = {
            "database": {
                "status": "ok" if db_ok else "error",
            }
        }
        if db_error is not None:
            checks["database"]["error"] = db_error

        ready = db_ok
        payload = {
            "status": "ok" if ready else "error",
            "checks": checks,
        }

        return Response(
            payload,
            status=HTTP_200_OK if ready else HTTP_503_SERVICE_UNAVAILABLE,
        )
