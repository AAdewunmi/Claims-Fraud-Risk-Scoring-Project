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
[![Test Coverage](https://img.shields.io/codecov/c/github/AAdewunmi/Claims-Fraud-Risk-Scoring-Project)](https://codecov.io/gh/AAdewunmi/Claims-Fraud-Risk-Scoring-Project)
[![Coverage Status](https://codecov.io/gh/AAdewunmi/Claims-Fraud-Risk-Scoring-Project/branch/main/graph/badge.svg)](https://codecov.io/gh/AAdewunmi/Claims-Fraud-Risk-Scoring-Project)

# UNDER CONSTRUCTION

# PolicyLens: Insurance Claims Fraud Risk Scoring System

PolicyLens is an insurance ops and compliance workflow tool built API-first for core workflows, with a server-rendered ops UI layered on top. It helps teams prioritise claims using fraud risk scoring, deterministic SLA rules, and exportable audit evidence.

Status timestamp: **February 17, 2026**.

## Product stance

API-first for core workflow, server-rendered UI for ops.

- DRF serializers define the canonical contract.
- Domain services implement workflow behaviour.
- Ops UI uses Django templates + HTMX without duplicating workflow logic.

## Milestone status (Implemented vs Planned)

### Implemented

- **Milestone W1 (January 2026):** Django/DRF project setup, healthcheck endpoint, Docker Compose dev stack.
- **Milestone W2 (January 2026):** Claims/documents/notes/decisions APIs, role-based decision permissions, sample data seeding.
- **Milestone W3 (February 2026):** Queue API ordering by SLA/priority, audit events API, JSON audit export, idempotency for write endpoints.
- **Milestone W4 (February 2026):** Fraud scoring persistence (score/label/reason codes + model metadata), training and scoring management commands.
- **Milestone W5 (started February 2026):** Ops UI shell and queue route; queue backend now uses shared queue builder logic.

### Planned

- **Milestone W5 completion target (February 18-21, 2026):** Claim detail UI route/template wiring and HTMX actions.
- **Milestone W6 target (late February 2026):** Evidence export polish and richer reviewer cues.
- **Milestone W7 target (March 2026):** Production deployment runbook (Render/VPS), production compose profile, and demo script.
- **Milestone W8 target (March 2026):** Performance checks and more edge-case/idempotency test coverage.

## Capabilities by status

### Implemented now (as of February 17, 2026)

- Claim and policy-change intake with structured metadata.
- Fraud risk scoring endpoint and persisted score metadata.
- Reviewer queue API prioritised by SLA and priority, with filtering.
- Document upload and metadata capture.
- Internal notes and decision history.
- Append-only audit events.
- Exportable audit evidence as JSON.
- Ops queue page (server-rendered) behind login.

### Planned (not fully shipped yet)

- Ops claim detail page with full timeline sections and actions.
- HTMX-driven create actions (notes, docs, decisions, scoring) from the UI.
- PDF audit export format.
- Production simulation stack with dedicated prod compose file + Nginx/Gunicorn profile.
- Demo script and docs/runbook directory.

## API surfaces

### Implemented endpoints

- `POST /api/claims/`
- `GET /api/claims/?status=&priority=`
- `GET /api/claims/{id}/`
- `POST /api/claims/{id}/documents/`
- `POST /api/claims/{id}/notes/`
- `POST /api/claims/{id}/decisions/`
- `POST /api/claims/{id}/ml-score/`
- `GET /api/queue/claims/`
- `GET /api/queue/claims/?status=&priority=&sla=breached|due_soon|ok`
- `GET /api/claims/{id}/audit-events/`
- `GET /api/claims/{id}/audit-export/`
- `GET /api/health/`

### Planned endpoints/formats

- `GET /api/claims/{id}/audit-export/?format=pdf` (planned format extension)

## Ops UI surfaces

### Implemented

- `/ops/` (redirect to queue)
- `/ops/queue/`

### Planned

- `/ops/claims/{id}/` claim detail page route and full template wiring

## Repository layout (current)

- `manage.py` Django management entrypoint
- `policylens/` project and apps
- `policylens/apps/claims/` domain models, services, API, export, ML, queue logic
- `policylens/apps/ops/` server-rendered UI
- `policylens/apps/core/` shared utilities (including idempotency)
- `tests/` pytest suite
- `artifacts/` local model artifacts

## Quickstart (development)

### Prerequisites

- Docker and Docker Compose

### Setup

1. Create env file:
   - `cp .env.example .env`
2. Start stack:
   - `docker compose up --build`
3. (Optional, if needed) run migrations manually:
   - `docker compose exec web python manage.py migrate --noinput`
4. Seed sample data (also seeds reviewer/admin users):
   - `docker compose exec web python manage.py seed_sample_data`
5. Open:
   - API health: `http://localhost:8000/api/health/`
   - Ops UI: `http://localhost:8000/ops/`

Demo users from seed command:
- `reviewer1 / password123`
- `admin1 / password123`

## Tests and quality gates

Run tests:

- `docker compose exec web pytest -q --cov=policylens --cov-config=.coveragerc --cov-report=term-missing --cov-report=xml --cov-fail-under=80`

Run lint and format checks:

- `docker compose exec web python -m ruff check .`
- `docker compose exec web python -m black . --check`

CI enforces:

- ruff
- black `--check`
- pytest with Postgres
- coverage threshold (`>= 80%`)

Coverage report:

- `https://codecov.io/gh/AAdewunmi/Claims-Fraud-Risk-Scoring-Project`

## Planned production simulation track

Planned artifacts (not present yet in this branch):

- `docker-compose.prod.yml`
- production web server profile (Gunicorn)
- Nginx reverse proxy configuration
- demo script (`scripts/demo.sh`)
- deployment docs/runbook directory

## Non-goals

- Replacing insurer core systems.
- Heavy ML research (the scoring layer is intentionally lightweight and governance-oriented).

## License

MIT License. See `LICENSE`.
