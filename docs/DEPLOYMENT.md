# PolicyLens deployment configuration

This document defines the production deployment shape for PolicyLens and the environment contract required to run safely behind Nginx.

## Deployment targets

PolicyLens provides two production-oriented Docker Compose profiles:

- `docker/docker-compose.prod.yml`
  - HTTP smoke profile for local validation (`http://localhost:8080`)
  - uses repo-root `.env`
- `docker/docker-compose.prod.secure.yml`
  - secure production-style profile
  - uses repo-root `.env.prod`

## Required environment variables

Minimum required variables for production runtime:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

Recommended security-related variables:

- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_SESSION_COOKIE_SECURE`
- `DJANGO_CSRF_COOKIE_SECURE`
- `DJANGO_SECURE_PROXY_SSL_HEADER`
- `DJANGO_USE_X_FORWARDED_HOST`
- `DJANGO_SECURE_HSTS_SECONDS`
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `DJANGO_SECURE_HSTS_PRELOAD`

## Reverse proxy contract

Nginx should forward requests to the Django/Gunicorn service and preserve host/proto information.

Expected route coverage:

- `/`
- `/login/*`
- `/console/*`
- `/customer/*`
- `/ops/*`
- `/api/*`

Expected proxy headers:

- `X-Forwarded-Proto`
- `Host`
- optional: `X-Forwarded-Host`

Static/media expectations:

- `/static/` served from `STATIC_ROOT` (default `/app/staticfiles`)
- `/media/` served from `MEDIA_ROOT` (default `/app/media`)

## Launch commands

HTTP smoke profile:

```bash
docker compose -f docker/docker-compose.prod.yml up --build -d
```

Secure profile:

```bash
docker compose -f docker/docker-compose.prod.secure.yml up --build -d
```

## Runtime behavior

The container entrypoint (`docker/entrypoint.sh`) performs deterministic startup tasks:

- waits for DB readiness
- runs migrations (unless disabled)
- runs collectstatic (unless disabled)
- starts the runtime command (Gunicorn)

For one-off admin commands, disable startup automation:

```bash
docker compose -f docker/docker-compose.prod.yml run --rm \
  -e RUN_MIGRATIONS=0 \
  -e RUN_COLLECTSTATIC=0 \
  web python manage.py migrate --noinput
```

## Post-deploy verification

Health:

```bash
curl -i http://localhost:8080/api/health/
```

Secure profile example (local port mapping):

```bash
curl -i http://localhost/api/health/
```

Expected:

- `200 OK`
- JSON body includes `{"status":"ok"}` and DB check status

Surface smoke checks:

- `/login/admin/`
- `/login/reviewer/`
- `/login/customer/`
- `/ops/queue/?page=2`
- `/customer/?page=2`

Evidence export checks:

- `GET /api/claims/{id}/audit-export/` (JSON)
- `GET /api/claims/{id}/audit-export/?format=pdf` (PDF)
