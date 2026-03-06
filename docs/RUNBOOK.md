# PolicyLens production stack runbook

Operational runbook for validating and operating PolicyLens in its production-shaped Docker profiles.

## Scope

This runbook covers:

- Nginx + Gunicorn runtime profile
- health verification
- multi-surface route verification
- proxy-safe pagination checks (`?page=2`)
- evidence export checks (JSON and PDF)

## Compose profiles

- HTTP smoke profile: `docker/docker-compose.prod.yml`
  - local endpoint: `http://localhost:8080`
  - env file: `.env`
- secure profile: `docker/docker-compose.prod.secure.yml`
  - local endpoint: `http://localhost`
  - env file: `.env.prod`

## Pre-flight

- Docker Desktop and Compose v2 installed
- `.env` and/or `.env.prod` present at repo root
- production secrets/hosts configured correctly for target environment

## Start stack

HTTP smoke profile:

```bash
docker compose -f docker/docker-compose.prod.yml up --build -d
```

Secure profile:

```bash
docker compose -f docker/docker-compose.prod.secure.yml up --build -d
```

## Health and readiness checks

HTTP smoke profile:

```bash
curl -i http://localhost:8080/api/health/
```

Secure profile:

```bash
curl -i http://localhost/api/health/
```

Expected:

- `200 OK`
- JSON contains `status: ok`
- JSON includes DB check status

## Surface checks

HTTP profile URLs:

- `http://localhost:8080/login/admin/`
- `http://localhost:8080/login/reviewer/`
- `http://localhost:8080/login/customer/`
- `http://localhost:8080/ops/queue/?page=2`
- `http://localhost:8080/customer/?page=2`

Secure profile URLs:

- `http://localhost/login/admin/`
- `http://localhost/login/reviewer/`
- `http://localhost/login/customer/`
- `http://localhost/ops/queue/?page=2`
- `http://localhost/customer/?page=2`

## API checks through proxy

Queue check:

```bash
curl -i -u reviewer1:password123 "http://localhost:8080/api/queue/claims/?priority=HIGH"
```

ML scoring check:

```bash
curl -i -u reviewer1:password123 -X POST "http://localhost:8080/api/claims/1/ml-score/"
```

Evidence export checks:

```bash
curl -i -u reviewer1:password123 "http://localhost:8080/api/claims/1/audit-export/"
curl -i -u reviewer1:password123 "http://localhost:8080/api/claims/1/audit-export/?format=pdf"
```

Expected evidence behavior:

- JSON response includes attachment filename ending `.json`
- PDF response has `Content-Type: application/pdf` and filename ending `.pdf`

## One-off admin commands

The production entrypoint runs DB wait, migrations, and collectstatic. For one-off commands, skip startup automations:

```bash
docker compose -f docker/docker-compose.prod.yml run --rm \
  -e RUN_MIGRATIONS=0 \
  -e RUN_COLLECTSTATIC=0 \
  web python manage.py migrate --noinput
```

## Stop stack

```bash
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.secure.yml down
```

## Troubleshooting

- `401 Unauthorized` on API calls
  - provide Basic auth (`-u user:pass`) or `--netrc-file`
- `404` on queue endpoint
  - use `/api/queue/claims/` (not `/api/claims/queue/`)
- `404` on ML endpoint
  - use `/api/claims/{id}/ml-score/` (not `/score/`)
- idempotency conflict
  - same key + different payload correctly returns `409`
