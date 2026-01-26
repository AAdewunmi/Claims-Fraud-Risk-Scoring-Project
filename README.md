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

PolicyLens is an insurance operations and compliance workflow prototype that helps teams prioritise claims for review using fraud risk scoring, deterministic SLA rules, and exportable audit evidence. This build focuses on API-first design, testable domain services, and production-minded delivery.

Work is in progress. The system runs end-to-end, but features, endpoints, and UI flows will continue to evolve as milestones are completed.

## What PolicyLens does

PolicyLens supports a reviewer workflow that brings risk and evidence into one place:

- Claim and policy-change intake with structured metadata
- Fraud risk scoring that persists a score, label, and reason codes
- Reviewer queue prioritised by SLA state and priority, with filtering
- Document upload and metadata capture
- Internal notes and decision history
- Append-only audit events for every action
- Exportable audit evidence as JSON, with PDF export available in later milestones
- Ops UI for queue and claim detail, built server-rendered with HTMX actions

## Product stance

API-first for core workflow, server-rendered UI for ops.

- DRF serializers define the canonical contract.
- Domain services implement behaviour shared by API and UI.
- Ops UI uses Django Templates, Bootstrap 5.3, and HTMX without duplicating workflow logic.

## Current status

In progress.

Implemented so far (high level):

- Django + DRF project structure with a service layer for workflows
- Core APIs for claims, documents, notes, decisions, queue, audit export
- Fraud risk scoring service persisting score, label, and reason codes
- Deterministic SLA classification and queue ordering
- Ops UI pages for queue and claim detail, including HTMX actions
- Docker Compose development setup (Django + Postgres)
- GitHub Actions CI running lint, format checks, tests, and coverage threshold
- Production-style packaging for local simulation (Gunicorn + Nginx)

Planned next:

- Fraud scoring governance polish, threshold documentation, and reviewer cues
- Evidence export polish, PDF layout improvements, and completeness checks
- Deployment target walkthrough (Render or small VPS) with a repeatable runbook
- Additional tests covering failure modes, idempotency, and edge cases
- Performance checks for queue queries and export endpoints

## Stack

- Django + Django REST Framework
- PostgreSQL
- Docker Compose
- pytest + pytest-django + factory_boy
- ruff + black
- GitHub Actions CI

## Repository layout

Typical structure:

- `manage.py` Django management entrypoint (repo root)
- `policylens/` Django project root
- `policylens/apps/claims/` domain models, services, API, exports, risk scoring
- `policylens/apps/ops/` server-rendered ops UI (templates + HTMX)
- `policylens/apps/core/` shared utilities, health checks, management commands
- `policylens/tests/` pytest test suite
- `docs/` deployment notes, runbook, demo script
- `docker/` entrypoint and Nginx configuration
- `artifacts/` model artefacts (generated locally)

Exact paths may change as the lab progresses.

## Quickstart (development)

### Prerequisites

- Docker and Docker Compose

### Setup

1. Create env file:
   - cp .env.example .env
2. Start the stack:
   - docker compose up --build
3. Run migrations:
   - docker compose exec web python manage.py migrate --noinput
4. Seed sample data
   - docker compose exec web python manage.py seed_sample_data
   - Note: seeding is deterministic and safe to re-run for demos.
5. Create demo users:
   - docker compose exec web python manage.py create_demo_users
6. Open:
   - API health: http://localhost:8000/api/health/
   - Ops UI: http://localhost:8000/ops/

Login uses the demo users created by the command above.

## Tests and quality gates

Run tests:

- docker compose exec web pytest -q

Run lint and format checks:

- docker compose exec web ruff check .
- docker compose exec web black --check .

CI enforces:
- ruff
- black --check
- pytest with Postgres
- coverage threshold

Coverage reports are uploaded to Codecov from CI. Since the repo is public, no token is required.
View the coverage report here:
```
https://codecov.io/gh/AAdewunmi/Claims-Fraud-Risk-Scoring-Project
```

## Local production simulation

A production-style stack is provided using Gunicorn and Nginx.

1. Copy env:
   - cp .env.example .env
2. Start production stack:
   - docker compose -f docker-compose.prod.yml up --build
3. Validate:
   - curl http://localhost:8080/api/health/

## Key API surfaces (selected)

These endpoints are treated as canonical and expanded throughout the lab:

- POST /api/claims/
- GET /api/claims/?status=&priority=
- POST /api/claims/{id}/documents/
- POST /api/claims/{id}/decisions/
- POST /api/claims/{id}/ml-score/  (fraud risk scoring)
- GET /api/queue/claims/
- GET /api/claims/{id}/audit-export/
- GET /api/claims/{id}/audit-export/?format=pdf

## Ops UI (selected)

- /ops/queue/
- /ops/claims/{id}/

HTMX actions support note creation, document upload, decision recording, and risk scoring without page reload.

## Demo

After starting the production stack:

- docker compose -f docker-compose.prod.yml exec web python manage.py create_demo_users
- bash scripts/demo.sh

The demo script runs a health check, creates sample data, triggers scoring, and fetches audit exports.

## Non-goals

- Replacing insurer core systems. This project focuses on the triage layer, fraud risk scoring, and audit evidence workflow.
- Heavy ML research. The scoring component is intentionally lightweight and governance-oriented.

## License

License
