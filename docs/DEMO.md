# PolicyLens demo

This demo shows Week 6 multi-surface behaviour with deterministic routing, role boundaries, and pagination.

## Prerequisites

The project should be running with the usual Docker Compose stack.

## Create demo users and demo claims

Run the demo seed command:

- docker compose exec web python manage.py create_demo_users

Expected output includes three demo users and counts showing at least 16 claims for:
- reviewer queue pagination
- customer claim list pagination

## Login entry points

Use the surface entry points, not Django admin login:

- Admin login: /login/admin/
- Reviewer login: /login/reviewer/
- Customer login: /login/customer/

Default demo password (set by the command):
- pass-12345-strong

## Consoles

After login, each entry point routes deterministically to its console:

- Admin console: /console/admin/
- Reviewer console: /console/reviewer/
- Customer console: /console/customer/

Admin console links to:
- Django admin: /admin/

## Pagination demonstrations

Page size is fixed at 15.

### Reviewer queue pagination

Reviewer (or admin) can open:

- /ops/queue/?page=1
- /ops/queue/?page=2

Expected:
- Both pages return 200
- Ordering is stable
- Pagination links preserve filters

### Customer claim list pagination

Customer (or admin) can open:

- /customer/?page=1
- /customer/?page=2

Expected:
- Both pages return 200
- Only customer-owned claims are listed
- Pagination links preserve query parameters

## Quick validation commands

Run the quality gates:

- docker compose exec web python manage.py check
- docker compose exec web python manage.py migrate
- docker compose exec web python -m black . --check
- docker compose exec web python -m ruff check .
- docker compose exec web pytest -q

Run the Sprint 6 smoke test:

- docker compose exec web pytest -q policylens/tests/test_surface_smoke.py