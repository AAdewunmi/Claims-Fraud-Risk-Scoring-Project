# path: docs/DEPLOYMENT.md
# PolicyLens deployment configuration

This document describes the environment variables and settings expectations for running PolicyLens behind an Nginx reverse proxy. The goal is a production profile that is safe by default without breaking role-based login flows or paginated list navigation.

## Surface routes

Nginx should route these prefixes to the Django app:

- / serves the public landing page
- /login/admin/, /login/reviewer/, and /login/customer/ serve surface entry points
- /console/admin/, /console/reviewer/, and /console/customer/ serve role consoles
- /customer/* serves customer pages
- /ops/* serves ops pages
- /api/* serves DRF endpoints, including /api/health/

Static and media routes are typically served by Nginx from shared volumes:

- /static/ from the collectstatic output directory (`STATIC_ROOT`, default `/app/staticfiles`)
- /media/ from the uploaded media directory (`MEDIA_ROOT`, default `/app/media`)

## Required environment variables

These must be set in the production runtime environment:

- DJANGO_SECRET_KEY
- DJANGO_ALLOWED_HOSTS
- DATABASE_URL
- DJANGO_CSRF_TRUSTED_ORIGINS

## Secure compose profile

For the secure Docker profile (`docker/docker-compose.prod.secure.yml`):

- `.env.prod` is ignored by `.gitignore` (`.env.*`) and is not committed.
- Replace all placeholder values in `.env.prod` before deployment.
- Launch with `docker compose -f docker/docker-compose.prod.secure.yml up --build`.

## Reverse proxy and HTTPS detection

Django must understand that the external client connection is HTTPS even though Nginx forwards requests to Django over HTTP. This is required for secure cookies, CSRF, and correct redirect behaviour.

Expected headers from Nginx:

- X-Forwarded-Proto: https
- Host: your public host

Optional header when you need it:

- X-Forwarded-Host: your public host

Settings involved:

- SECURE_PROXY_SSL_HEADER is enabled via DJANGO_SECURE_PROXY_SSL_HEADER
- USE_X_FORWARDED_HOST is enabled via DJANGO_USE_X_FORWARDED_HOST

Note:

- `LOGIN_URL` is set to `/login/` in settings as a framework default.
- Product surface logins are routed at `/login/admin/`, `/login/reviewer/`, and `/login/customer/`.

## CSRF trusted origins

When running behind a proxy, CSRF validation requires the deployed origin to be explicitly trusted. Django expects scheme-qualified origins.

Set DJANGO_CSRF_TRUSTED_ORIGINS as a comma separated list, for example:

- https://policylens.example.com
- https://www.policylens.example.com

If this is missing or wrong, login POSTs and other form submissions will fail with 403 CSRF errors.

## Secure cookies

When DEBUG is off, the production default is to enable secure cookies:

- SESSION_COOKIE_SECURE
- CSRF_COOKIE_SECURE

These require HTTPS at the browser. If you test locally without TLS, override:

- DJANGO_SESSION_COOKIE_SECURE=0
- DJANGO_CSRF_COOKIE_SECURE=0
- DJANGO_SECURE_SSL_REDIRECT=0

When running with real HTTPS termination, keep them enabled.

## Recommended production flags

These are available as environment variables but are intentionally conservative by default:

- DJANGO_SECURE_SSL_REDIRECT
- DJANGO_SECURE_HSTS_SECONDS
- DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS
- DJANGO_SECURE_HSTS_PRELOAD

Enable HSTS only once the domain, HTTPS termination, and redirects are stable.

## Quick verification checklist

These checks are the minimum proof that proxy and security settings did not break the product surfaces:

- /login/admin/, /login/reviewer/, /login/customer/ accept credentials and establish a session
- /ops/queue/?page=2 loads after login and keeps pagination links working
- /customer/?page=2 loads after login and keeps pagination links working
- /api/health/ returns 200 with status ok
