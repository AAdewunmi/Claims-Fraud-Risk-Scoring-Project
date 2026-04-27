[![CI Pipeline](https://img.shields.io/github/actions/workflow/status/AAdewunmi/Claims-Fraud-Risk-Scoring-Project/ci.yml?branch=main)](https://github.com/AAdewunmi/Claims-Fraud-Risk-Scoring-Project/actions/workflows/ci.yml)
[![Code Style - Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/)
[![Lint - Ruff](https://img.shields.io/badge/lint-ruff-000000.svg)](https://docs.astral.sh/ruff/)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.x-0C4B33.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/docker-enabled-2496ED.svg)](https://www.docker.com/)
[![Docker Compose](https://img.shields.io/badge/docker%20compose-supported-2496ED.svg)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/github/license/AAdewunmi/Claims-Fraud-Risk-Scoring-Project)](https://github.com/AAdewunmi/Claims-Fraud-Risk-Scoring-Project/blob/main/LICENSE)
[![Coverage Status](https://codecov.io/gh/AAdewunmi/Claims-Fraud-Risk-Scoring-Project/branch/main/graph/badge.svg)](https://codecov.io/gh/AAdewunmi/Claims-Fraud-Risk-Scoring-Project)

# PolicyLens

Production-ready insurance claims workflow platform with an API-first domain model, role-specific operational surfaces, ML-assisted completeness scoring, and auditable evidence export.

## Project Status

Completed.

As of March 6, 2026, PolicyLens includes the full Sprint 1-7 scope:

- End-to-end claims workflow APIs (create, retrieve, documents, notes, decisions).
- SLA-aware operational queue with deterministic filtering and ordering.
- Multi-surface routing for admin, reviewer, and customer user journeys.
- Health/readiness endpoint for runtime and infrastructure checks.
- Idempotency protection for write endpoints.
- ML scoring with persisted metadata and reason codes.
- Audit evidence export in JSON and PDF.
- Production-shaped Docker stack with Gunicorn + Nginx profiles.
- CI gates for Black, Ruff, pytest, and coverage threshold enforcement.

## Core Capabilities

### API and domain workflow

- Claim intake for `CLAIM` and `POLICY_CHANGE` types.
- Document upload, internal note capture, and reviewer decisioning.
- Append-only audit events attached to workflow actions.
- Queue endpoint with `status`, `priority`, and SLA filter options.
- Idempotency-key support for safe client retries on write endpoints.

### Ops and customer surfaces

- Public landing page and role entry routes.
- Role-gated console routes for admin/reviewer/customer.
- Reviewer ops queue and claim detail with HTMX actions.
- Customer claim list/detail views with pagination.

### Evidence and ML

- JSON evidence bundle export for claim audits.
- PDF evidence bundle export for portability/compliance workflows.
- ML completeness scoring endpoint with:
  - score
  - label
  - reason codes
  - model version metadata

## Landing Page

<img width="800" height="617" alt="Image" src="https://github.com/user-attachments/assets/0cfa9384-33f5-4141-a495-299cdfc88303" />

## API Surface

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
- `GET /api/claims/{id}/audit-export/?format=pdf`
- `GET /api/queue/claims/?status=&priority=&sla=breached|due_soon|ok`

## Architecture

- Backend: Django + Django REST Framework
- Database: PostgreSQL
- Frontend: Django Templates + HTMX (server-rendered interactions)
- ML: scikit-learn inference and persisted scoring metadata
- Runtime: Docker Compose, Gunicorn, Nginx

## Technologies Used

- Language/runtime: Python 3.11
- Backend framework: Django 5.x
- API framework: Django REST Framework 3.15.x
- Database: PostgreSQL 16 (Docker image: `postgres:16-alpine`)
- UI layer: Django Templates, HTMX 1.9.12, Bootstrap 5.3.3, custom CSS
- ML stack: scikit-learn, NumPy, joblib
- App server: Gunicorn
- Reverse proxy: Nginx 1.27 (Docker image: `nginx:1.27-alpine`)
- Environment/config: `django-environ`
- Containerization: Docker + Docker Compose
- Testing: pytest, pytest-django, pytest-cov, factory-boy, Faker
- Code quality: Ruff, Black, Flake8
- CI/coverage: GitHub Actions, Codecov

Key modules:

- `policylens/apps/claims/` domain logic, APIs, queue, export, ML
- `policylens/apps/core/` authz, idempotency, pagination utilities
- `policylens/apps/ops/` reviewer workflows and HTMX endpoints
- `policylens/apps/customer/` customer workflow surface
- `policylens/apps/api/` top-level API wiring and health endpoint

## Repository Structure

```text
.
├── policylens/
│   ├── apps/
│   │   ├── accounts/        # auth/login surfaces
│   │   ├── api/             # top-level API routes and health
│   │   ├── claims/          # claims domain, APIs, queue, export, ML
│   │   ├── console/         # role-specific console views
│   │   ├── core/            # shared authz/idempotency/pagination utilities
│   │   ├── customer/        # customer-facing workflows
│   │   ├── ops/             # reviewer ops UI + HTMX endpoints
│   │   └── public/          # public landing routes/views
│   ├── config/              # Django settings, URL config, ASGI/WSGI
│   ├── templates/           # shared templates
│   └── static/              # shared static assets
├── tests/                   # pytest suite (API, UI, ML, authz, SLA)
├── docs/                    # deployment, runbook, demo and syllabus docs
├── docker/                  # production Dockerfiles, nginx, gunicorn config
├── scripts/                 # helper scripts (for demos/local workflows)
├── artifacts/               # generated artifacts/evidence output
├── media/                   # uploaded files (local/dev)
├── docker-compose.yml       # local dev stack
├── Dockerfile               # local/dev image build
└── manage.py                # Django management entrypoint
```

## Local Development

### Prerequisites

- Docker Desktop with Compose v2

### Quick start

1. Copy environment file:
   - `cp .env.example .env`
2. Start the app stack:
   - `docker compose up --build`
3. Seed baseline records and users:
   - `docker compose exec web python manage.py seed_sample_data`
4. Optional: add expanded demo users/data:
   - `docker compose exec web python manage.py create_demo_users`
5. Open:
   - `http://localhost:8000/`
   - `http://localhost:8000/api/health/`
   - `http://localhost:8000/ops/queue/`

### Seeded credentials

From `seed_sample_data`:

- `reviewer1 / password123`
- `admin1 / password123`

From `create_demo_users`:

- `demo_admin / pass-12345-strong`
- `demo_reviewer / pass-12345-strong`
- `demo_customer / pass-12345-strong`

## Production-shaped profiles

HTTP smoke profile:

- `docker compose -f docker/docker-compose.prod.yml up --build -d`
- App entrypoint: `http://localhost:8080/`

Secure profile:

- `docker compose -f docker/docker-compose.prod.secure.yml up --build -d`
- App entrypoint: `http://localhost/`

See:

- `docs/DEPLOYMENT.md`
- `docs/RUNBOOK.md`

## Quality and Validation

Local validation commands:

- `docker compose exec web python -m black . --check`
- `docker compose exec web python -m ruff check .`
- `docker compose exec web pytest -q --cov=policylens --cov-config=.coveragerc --cov-report=term-missing --cov-report=xml --cov-fail-under=85`

Latest local full suite run:

- `201 passed in 103.68s` (March 6, 2026)

CI gates enforce:

- formatting (`black --check`)
- lint (`ruff check`)
- migrations + collectstatic sanity
- pagination-first test execution
- full test suite with coverage threshold

## Documentation

- `docs/DEPLOYMENT.md` production configuration and environment guidance
- `docs/RUNBOOK.md` operational runbook for prod-shaped stacks
- `docs/DEMO.md` manual demo checklist
- `docs/DEMO_SCRIPT.md` automated demo script usage
- `docs/Syllabus.md` complete sprint-by-sprint delivery map

## License

MIT. See `LICENSE`.
