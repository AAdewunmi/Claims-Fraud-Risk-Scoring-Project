# PolicyLens Sprint 7 demo script

This guide documents the automated demo flow implemented in `scripts/demo.sh`.

The script is intended for production-shaped validation, not the default dev compose file.

## What the script validates

- stack boots behind Nginx with Gunicorn
- DB migrations and baseline seed run successfully
- reviewer and customer pagination links survive the proxy boundary (`?page=2`)
- health endpoint returns through proxy
- evidence export works in both JSON and PDF formats

## Run

From the repository root:

```bash
bash scripts/demo.sh
```

Optional overrides:

```bash
COMPOSE_FILE=docker/docker-compose.prod.yml bash scripts/demo.sh
COMPOSE_FILE=docker/docker-compose.prod.secure.yml PROXY_URL=http://localhost bash scripts/demo.sh
```

## Expected output highlights

- stack startup banner and compose profile
- seeded demo user info and generated claim id for export checks
- successful `curl -I` checks for:
  - `/ops/queue/?page=2`
  - `/customer/?page=2`
- printed JSON and PDF evidence export commands
- downloaded files:
  - `claim_<id>_audit_export.json`
  - `claim_<id>_audit_export.pdf`

## Notes

- script enforces prod-shaped compose usage (`COMPOSE_FILE` containing `prod`)
- default proxy URL is `http://localhost:8080`
- secure profile maps Nginx on port 80 by default; set `PROXY_URL=http://localhost`
