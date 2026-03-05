#!/bin/sh
#
# Container entrypoint for PolicyLens.
#
# Responsibilities
# - Wait for the primary database to become reachable
# - Run migrations deterministically
# - Run collectstatic deterministically
# - Hand off to the container command (for example Gunicorn)
#
# Environment variables
# - DJANGO_SETTINGS_MODULE: Django settings module (default: policylens.config.settings)
# - WAIT_FOR_DB_ATTEMPTS: number of DB readiness attempts (default: 30)
# - WAIT_FOR_DB_SECONDS: sleep interval between attempts (default: 2)
# - RUN_MIGRATIONS: set to 0 to skip migrations (default: 1)
# - RUN_COLLECTSTATIC: set to 0 to skip collectstatic (default: 1)
# - DJANGO_RUN_MIGRATIONS: legacy alias for RUN_MIGRATIONS
# - DJANGO_COLLECTSTATIC: legacy alias for RUN_COLLECTSTATIC

set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-policylens.config.settings}"
WAIT_FOR_DB_ATTEMPTS="${WAIT_FOR_DB_ATTEMPTS:-30}"
WAIT_FOR_DB_SECONDS="${WAIT_FOR_DB_SECONDS:-2}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-${DJANGO_RUN_MIGRATIONS:-1}}"
RUN_COLLECTSTATIC="${RUN_COLLECTSTATIC:-${DJANGO_COLLECTSTATIC:-1}}"

echo "PolicyLens entrypoint starting."
echo "Using settings module: ${DJANGO_SETTINGS_MODULE}"

python - <<'PY'
"""
Wait for the default database connection to become ready.

This uses Django's configured database connection so the check stays aligned
with the actual runtime settings and DATABASE_URL.
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "policylens.config.settings"),
)

import django  # noqa: E402

django.setup()

from django.db import connections  # noqa: E402

attempts = int(os.getenv("WAIT_FOR_DB_ATTEMPTS", "30"))
sleep_seconds = int(os.getenv("WAIT_FOR_DB_SECONDS", "2"))

for attempt in range(1, attempts + 1):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()

        if row and row[0] == 1:
            print(f"Database is ready on attempt {attempt}.")
            break

        print(f"Database returned an unexpected readiness result on attempt {attempt}.")
    except Exception as exc:  # noqa: BLE001
        print(
            f"Database not ready on attempt {attempt}/{attempts}: "
            f"{exc.__class__.__name__}: {exc}"
        )

    if attempt == attempts:
        print("Database readiness check exhausted all retries.")
        sys.exit(1)

    time.sleep(sleep_seconds)
PY

if [ "${RUN_MIGRATIONS}" = "1" ]; then
  echo "Running migrations."
  python manage.py migrate --noinput
else
  echo "Skipping migrations because RUN_MIGRATIONS=${RUN_MIGRATIONS}."
fi

if [ "${RUN_COLLECTSTATIC}" = "1" ]; then
  echo "Running collectstatic."
  python manage.py collectstatic --noinput --clear
else
  echo "Skipping collectstatic because RUN_COLLECTSTATIC=${RUN_COLLECTSTATIC}."
fi

echo "Entrypoint complete. Starting command: $*"
exec "$@"
