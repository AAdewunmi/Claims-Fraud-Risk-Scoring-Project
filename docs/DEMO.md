# PolicyLens demo (completed project)

This checklist validates the complete Sprint 7 experience across API, surfaces, pagination, and evidence export.

## Prerequisites

- Docker Desktop running
- Repo-root `.env` present (`cp .env.example .env` if needed)

## Start and seed

```bash
docker compose up --build -d
docker compose exec web python manage.py migrate --noinput
docker compose exec web python manage.py seed_sample_data
docker compose exec web python manage.py create_demo_users
```

## Baseline quality checks

```bash
docker compose exec web python -m black . --check
docker compose exec web python -m ruff check .
docker compose exec web pytest -q
```

Expected:

- formatter/lint checks pass
- full test suite passes

## Health and routing

```bash
curl -i http://localhost:8000/api/health/
```

Expected:

- `200 OK`
- JSON payload includes service status and DB readiness check

## Surface entry points

- `http://localhost:8000/login/admin/`
- `http://localhost:8000/login/reviewer/`
- `http://localhost:8000/login/customer/`

## Pagination proof points

- Reviewer queue page 1: `http://localhost:8000/ops/queue/?page=1`
- Reviewer queue page 2: `http://localhost:8000/ops/queue/?page=2`
- Customer list page 1: `http://localhost:8000/customer/?page=1`
- Customer list page 2: `http://localhost:8000/customer/?page=2`

## API checks

### Idempotent claim creation

Use `sample-claim.json` and `sample-claim-changed.json` from repo root.

```bash
curl --netrc-file .curl-auth -i -X POST http://localhost:8000/api/claims/ \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-key-001" \
  -d @sample-claim.json

curl --netrc-file .curl-auth -i -X POST http://localhost:8000/api/claims/ \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-key-001" \
  -d @sample-claim.json

curl --netrc-file .curl-auth -i -X POST http://localhost:8000/api/claims/ \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-key-001" \
  -d @sample-claim-changed.json
```

Expected status flow: `201`, `201`, `409`.

### Queue and ML

```bash
curl --netrc-file .curl-auth -i "http://localhost:8000/api/queue/claims/?priority=HIGH"
curl --netrc-file .curl-auth -i -X POST "http://localhost:8000/api/claims/1/ml-score/"
```

### Evidence export

```bash
curl --netrc-file .curl-auth -i "http://localhost:8000/api/claims/1/audit-export/"
curl --netrc-file .curl-auth -i "http://localhost:8000/api/claims/1/audit-export/?format=pdf"
```

Expected:

- JSON export returns attachment filename ending `.json`
- PDF export returns `Content-Type: application/pdf` and attachment filename ending `.pdf`
