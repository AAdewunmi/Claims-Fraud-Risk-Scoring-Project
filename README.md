[![CI Pipeline](https://img.shields.io/github/actions/workflow/status/AAdewunmi/Claims-Fraud-Risk-Scoring-Project/ci.yml?branch=main)](https://github.com/AAdewunmi/Claims-Fraud-Risk-Scoring-Project/actions/workflows/ci.yml)
[![Code Style - Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/)
[![Lint - Ruff](https://img.shields.io/badge/lint-ruff-000000.svg)](https://docs.astral.sh/ruff/)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.x-0C4B33.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/docker-enabled-2496ED.svg)](https://www.docker.com/)
[![Docker Compose](https://img.shields.io/badge/docker%20compose-supported-2496ED.svg)](https://docs.docker.com/compose/)
[![Licence](https://img.shields.io/github/license/AAdewunmi/Claims-Fraud-Risk-Scoring-Project)](https://github.com/AAdewunmi/Claims-Fraud-Risk-Scoring-Project/blob/main/LICENSE)
[![Coverage Status](https://codecov.io/gh/AAdewunmi/Claims-Fraud-Risk-Scoring-Project/branch/main/graph/badge.svg)](https://codecov.io/gh/AAdewunmi/Claims-Fraud-Risk-Scoring-Project)

# PolicyLens

Insurance claims workflow platform with API-first domain logic, role-specific web surfaces, and auditable fraud-risk triage.

## Status

**Production app build in progress**  
Snapshot date: **February 28, 2026**

- Core product workflows are implemented and running in Docker.
- CI quality gates are active (Black, Ruff, pytest, coverage threshold).
- Multi-surface routing is live for admin, reviewer, and customer roles.
- Production deployment profile and operational hardening are the active build track.

## What is live today

### Core domain and API

- Claim intake for claim and policy-change types.
- Document upload, internal notes, and review decisions.
- Append-only audit events and JSON evidence export.
- Queue API with status, priority, and SLA filtering.
- ML scoring endpoint with persisted score metadata and reason codes.
- Idempotency support for write endpoints.
- Health check endpoint at `/api/health/`.

### Web surfaces

- Public landing page with role entry points.
- Surface-specific login routes:
  - `/login/admin/`
  - `/login/reviewer/`
  - `/login/customer/`
- Role-gated console home routes:
  - `/console/admin/`
  - `/console/reviewer/`
  - `/console/customer/`
- Ops surface:
  - `/ops/queue/` with pagination and filter-preserving links
  - `/ops/claims/{id}/` claim detail page
  - HTMX actions for notes, documents, decisions, and ML scoring
- Customer surface:
  - `/customer/` paginated claim list
  - `/customer/claims/{id}/` detail view
  - `/customer/claims/{id}/documents/upload/`

### Quality baseline

- Latest local run: **166 tests passed**, coverage **94.43%**.
- CI enforces coverage floor at **80%**.
- Test suite includes API, UI surface, authz, pagination, idempotency, SLA, and ML contract checks.

## Sprint delivery summary

- **Sprint 1:** Project setup, Docker + Postgres, baseline API and test harness.
- **Sprint 2:** Claim workflow APIs, notes/documents/decisions, seed data path.
- **Sprint 3:** Queue ordering, audit events, audit export JSON, idempotency layer.
- **Sprint 4:** ML feature contract, training/scoring flow, persisted score metadata.
- **Sprint 5:** Multi-surface web app, console routing, ops and customer surface coverage.
- **Sprint 6 (current):** Production hardening and deployment readiness.

## API surface map

- `GET /api/health/`
- `POST /api/claims/`
- `GET /api/claims/?status=&priority=`
- `GET /api/claims/{id}/`
- `POST /api/claims/{id}/documents/`
- `POST /api/claims/{id}/notes/`
- `POST /api/claims/{id}/decisions/`
- `POST /api/claims/{id}/ml-score/`
- `GET /api/claims/{id}/audit-events/`
- `GET /api/claims/{id}/audit-export/`
- `GET /api/queue/claims/?status=&priority=&sla=breached|due_soon|ok`

## Architecture

- Django + DRF application (`policylens/`) with PostgreSQL persistence.
- Service-layer workflow logic in `policylens/apps/claims/services.py`.
- Role and surface authorization helpers in `policylens/apps/core/authz.py`.
- Shared pagination contract in `policylens/apps/core/pagination.py`.
- Server-rendered templates with HTMX partial updates for low-friction ops actions.

## Local development

### Prerequisites

- Docker Desktop with Compose v2

### Quick start

1. Copy environment file:
   - `cp .env.example .env`
2. Build and start services:
   - `docker compose up --build`
3. Seed deterministic sample records:
   - `docker compose exec web python manage.py seed_sample_data`
4. Seed demo users and pagination-focused demo claims:
   - `docker compose exec web python manage.py create_demo_users`
5. Open app surfaces:
   - `http://localhost:8000/`
   - `http://localhost:8000/api/health/`
   - `http://localhost:8000/ops/queue/`

### Seeded users

From `seed_sample_data`:

- `reviewer1 / password123`
- `admin1 / password123`

From `create_demo_users`:

- `demo_admin / pass-12345-strong`
- `demo_reviewer / pass-12345-strong`
- `demo_customer / pass-12345-strong`

## Validation commands

- `docker compose exec web python -m black . --check`
- `docker compose exec web python -m ruff check .`
- `docker compose exec web pytest -q --cov=policylens --cov-config=.coveragerc --cov-report=term-missing --cov-report=xml --cov-fail-under=80`

## Production hardening backlog

Current priority items for deployment readiness:

- Add production runtime profile (Gunicorn + reverse proxy).
- Add production compose/deploy artifacts and environment split.
- Tighten security settings by environment (hosts, cookies, headers, static/media strategy).
- Introduce scheduled/background execution for SLA sweep and bulk scoring.
- Extend evidence export format options (for example PDF).

## Repository layout

- `policylens/apps/claims/` claims domain, API, queue, export, ML
- `policylens/apps/ops/` ops views, templates, HTMX endpoints
- `policylens/apps/customer/` customer portal views and templates
- `policylens/apps/accounts/` surface login and access flows
- `policylens/apps/console/` role console surfaces
- `policylens/apps/core/` authz, idempotency, pagination utilities
- `tests/` integration and contract tests
- `docs/` project documentation

## License

MIT. See `LICENSE`.
