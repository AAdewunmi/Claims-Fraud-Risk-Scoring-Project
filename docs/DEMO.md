# PolicyLens demo

This demo validates Sprint 6 multi-surface behavior with deterministic routing,
role boundaries, and pagination.

## Prerequisites

The project should already be running via Docker Compose.

## Login entry points

Use the surface entry points:

- Admin login: `/login/admin/`
- Reviewer login: `/login/reviewer/`
- Customer login: `/login/customer/`

## Console-only runbook

Run:

- `docker compose exec web python manage.py check`
- `docker compose exec web python manage.py migrate`
- `docker compose exec web python -m black . --check`
- `docker compose exec web python -m ruff check .`
- `docker compose exec web pytest -q`
- `docker compose exec web python manage.py seed_sample_data`
- `docker compose exec web pytest -q tests/test_surface_smoke.py`

Expected:

- `check`, `migrate`, `black --check`, and `ruff check` complete without errors.
- `pytest -q` passes.
- `seed_sample_data` prints:
  `Seeded roles (reviewer, admin), users (reviewer1/admin1), holders, policies, claims.`
- `tests/test_surface_smoke.py` passes and validates `?page=1` and `?page=2` return `200`
  for the relevant reviewer and customer surfaces.

## Seeded local credentials

From `seed_sample_data`:

- `reviewer1 / password123`
- `admin1 / password123`
