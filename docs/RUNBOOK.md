# path: docs/RUNBOOK.md
# PolicyLens production stack runbook

This runbook proves PolicyLens runs behind an Nginx reverse proxy with Gunicorn, and that querystring pagination survives the proxy boundary. The checks are designed for Sprint 7, where each surface can be validated without hand edits, and page 2 is a deliberate proof point rather than a lucky accident.

Two compose profiles exist for production-shaped validation. The HTTP profile is for local smoke validation on `localhost:8080`. The secure profile is for a production-style settings shape where secure cookies and redirect behaviour are enabled, and it is intended to match the deployed environment rather than a laptop.

## Pre-flight

PolicyLens currently has two production-oriented compose profiles:

- `docker/docker-compose.prod.yml` for local smoke validation on HTTP (`localhost:8080`)
- `docker/docker-compose.prod.secure.yml` for secure production-style settings

Important:

- `docker/docker-compose.prod.yml` reads `../.env` (repo root `.env`).
- `docker/docker-compose.prod.secure.yml` reads `../.env.prod` (repo root `.env.prod`).
- `.env.prod` is ignored by `.gitignore` (`.env.*`), so it exists locally but is not tracked in git.
- Replace placeholder values in `.env.prod` before deployment.

## Start the production stack (HTTP profile)

```bash
docker compose -f docker/docker-compose.prod.yml up --build -d
```

## Secure profile launch

```bash
docker compose -f docker/docker-compose.prod.secure.yml up --build -d
```

## Smoke checks

Run these once the selected stack is up:

For HTTP profile (`prod.yml`):

```bash
curl -i http://localhost:8080/api/health/
```

For secure profile (`prod.secure.yml`, mapped on port 80):

```bash
curl -i http://localhost/api/health/
```

Expected:

- HTTP `200`
- JSON body contains `"status":"ok"`

### Surface checks

HTTP profile:

- `http://localhost:8080/login/admin/`
- `http://localhost:8080/login/reviewer/`
- `http://localhost:8080/login/customer/`
- `http://localhost:8080/ops/queue/?page=2`
- `http://localhost:8080/customer/?page=2`

Secure profile:

- `http://localhost/login/admin/`
- `http://localhost/login/reviewer/`
- `http://localhost/login/customer/`
- `http://localhost/ops/queue/?page=2`
- `http://localhost/customer/?page=2`

## One-off admin commands

For one-off commands (migrations, seeding, etc.), use `run --rm`:

```bash
docker compose -f docker/docker-compose.prod.yml run --rm \
  -e RUN_MIGRATIONS=0 \
  -e RUN_COLLECTSTATIC=0 \
  web python manage.py migrate --noinput
```

Note: the production entrypoint waits for DB readiness and runs migrations plus `collectstatic` before any command. For one-off `manage.py` commands, set `RUN_MIGRATIONS=0` and `RUN_COLLECTSTATIC=0` to avoid duplicate startup tasks.

## Stop the stack

```bash
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.secure.yml down
```
