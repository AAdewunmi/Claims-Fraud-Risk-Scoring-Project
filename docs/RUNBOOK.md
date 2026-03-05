# path: docs/RUNBOOK.md
# PolicyLens production stack runbook

This runbook proves that PolicyLens runs behind an Nginx reverse proxy with Gunicorn, and that querystring pagination survives the proxy path. The checks are designed to match Sprint 7 expectations, where the demo is repeatable and surfaces behave consistently.

## Pre-flight

PolicyLens currently has two production-oriented compose profiles:

- `docker/docker-compose.prod.yml` for local smoke validation on HTTP (`localhost:8080`)
- `docker/docker-compose.prod.secure.yml` for secure production-style settings

Important:

- `.env.prod` is ignored by `.gitignore` (`.env.*`), so it exists locally but is not tracked in git.
- Replace placeholder values in `.env.prod` before deployment.
- Run `docker compose -f docker/docker-compose.prod.secure.yml up --build` to launch the secure profile.

## Start the production stack

```bash
docker compose -f docker/docker-compose.prod.yml up --build -d
```

## Secure profile launch

```bash
docker compose -f docker/docker-compose.prod.secure.yml up --build
```

## Smoke checks

Run these once the stack is up:

```bash
curl -i http://localhost:8080/api/health/
```

Expected:

- HTTP `200`
- JSON body contains `"status": "ok"`

### Surface checks

- `http://localhost:8080/login/admin/`
- `http://localhost:8080/login/reviewer/`
- `http://localhost:8080/login/customer/`
- `http://localhost:8080/ops/queue/?page=2`
- `http://localhost:8080/customer/?page=2`

## One-off admin commands

For one-off commands (migrations, seeding, etc.), use `run --rm`:

```bash
docker compose -f docker/docker-compose.prod.yml run --rm \
  -e RUN_MIGRATIONS=0 \
  -e RUN_COLLECTSTATIC=0 \
  web python manage.py migrate --noinput
```

Note: the production entrypoint now waits for DB readiness and runs migrations plus `collectstatic` before any command. For one-off `manage.py` commands, set `RUN_MIGRATIONS=0` and `RUN_COLLECTSTATIC=0` to avoid duplicate startup tasks.

## Stop the stack

```bash
docker compose -f docker/docker-compose.prod.yml down
```
