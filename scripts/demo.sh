#!/usr/bin/env bash

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker/docker-compose.prod.yml}"
PROXY_URL="${PROXY_URL:-http://localhost:8080}"

echo "PolicyLens Sprint 7 demo"
echo ""
echo "Compose file: ${COMPOSE_FILE}"
echo "Public URL (proxy): ${PROXY_URL}"
echo ""

command -v docker >/dev/null 2>&1 || { echo "docker is required"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "docker compose is required"; exit 1; }

if [[ "${COMPOSE_FILE}" != *prod* ]]; then
  echo "This script is intended for prod-shaped compose files."
  echo "Use COMPOSE_FILE=docker/docker-compose.prod.yml (or prod.secure.yml)."
  exit 1
fi

COMPOSE_CMD=(docker compose -f "${COMPOSE_FILE}")

echo "Starting prod-shaped stack"
echo ""
"${COMPOSE_CMD[@]}" up --build -d

echo ""
echo "Applying migrations"
echo ""
"${COMPOSE_CMD[@]}" exec -T web python manage.py migrate --noinput

echo ""
echo "Seeding baseline records"
echo ""
"${COMPOSE_CMD[@]}" exec -T web python manage.py seed_sample_data

echo ""
echo "Creating deterministic demo data for pagination on both surfaces"
echo ""

DEMO_OUTPUT="$(
  "${COMPOSE_CMD[@]}" exec -T web python manage.py shell -c '
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from policylens.apps.claims.models import Claim, Policy, PolicyHolder

User = get_user_model()

customer_group, _ = Group.objects.get_or_create(name="customer")

u, _ = User.objects.get_or_create(
    username="demo_customer",
    defaults={"email": "demo_customer@example.com"},
)
u.set_password("pass-12345-strong")
u.save()
u.groups.add(customer_group)

holder, _ = PolicyHolder.objects.get_or_create(
    email="demo_customer@example.com",
    defaults={"full_name": "Demo Customer", "phone": ""},
)
policy, _ = Policy.objects.get_or_create(
    policy_number="PL-DEMO-CUST",
    defaults={
        "holder": holder,
        "product_type": "Home Insurance",
        "status": Policy.Status.ACTIVE,
    },
)

customer_existing = Claim.objects.filter(created_by=u.username).count()
customer_target = 25
customer_needed = max(0, customer_target - customer_existing)

for i in range(customer_needed):
    Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        status=Claim.Status.NEW,
        priority=Claim.Priority.NORMAL,
        summary=f"Demo customer claim {i + 1 + customer_existing}",
        created_by=u.username,
    )

ops_existing = Claim.objects.count()
ops_target = 35
ops_needed = max(0, ops_target - ops_existing)

for i in range(ops_needed):
    Claim.objects.create(
        policy=policy,
        claim_type=Claim.Type.CLAIM,
        status=Claim.Status.NEW,
        priority=Claim.Priority.NORMAL,
        summary=f"Demo ops claim {i + 1}",
        created_by="demo_seed",
    )

claim_for_export = Claim.objects.order_by("-created_at", "id").first()
print(f"DEMO_CUSTOMER=demo_customer")
print(f"DEMO_CUSTOMER_PASSWORD=pass-12345-strong")
print(f"DEMO_POLICY_NUMBER=PL-DEMO-CUST")
print(f"DEMO_CLAIM_ID_FOR_EXPORT={claim_for_export.id if claim_for_export else 0}")
'
)"

echo "${DEMO_OUTPUT}"
echo ""

DEMO_CLAIM_ID_FOR_EXPORT="$(echo "${DEMO_OUTPUT}" | awk -F= '/DEMO_CLAIM_ID_FOR_EXPORT/ {print $2}' | tr -d '\r')"

echo "Health check (proxy)"
echo ""
curl -i "${PROXY_URL}/api/health/" | head -n 20
echo ""

echo "Routing proof for paginated URLs through proxy"
echo ""
curl -I "${PROXY_URL}/ops/queue/?page=2" | head -n 20
echo ""
curl -I "${PROXY_URL}/customer/?page=2" | head -n 20
echo ""

echo "Reviewer surface URLs"
echo ""
echo "${PROXY_URL}/login/reviewer/"
echo "${PROXY_URL}/ops/queue/?page=1"
echo "${PROXY_URL}/ops/queue/?page=2"
echo ""
echo "Customer surface URLs"
echo ""
echo "${PROXY_URL}/login/customer/"
echo "${PROXY_URL}/customer/?page=1"
echo "${PROXY_URL}/customer/?page=2"
echo ""

echo "Evidence export URLs for claim id ${DEMO_CLAIM_ID_FOR_EXPORT}"
echo ""
echo "JSON export"
echo "curl -i -u reviewer1:password123 \"${PROXY_URL}/api/claims/${DEMO_CLAIM_ID_FOR_EXPORT}/audit-export/\""
echo ""
echo "Fetching JSON export into ./claim_${DEMO_CLAIM_ID_FOR_EXPORT}_audit_export.json"
echo ""
curl -sS -u reviewer1:password123 \
  "${PROXY_URL}/api/claims/${DEMO_CLAIM_ID_FOR_EXPORT}/audit-export/" \
  -o "claim_${DEMO_CLAIM_ID_FOR_EXPORT}_audit_export.json"

echo ""
echo "PDF export is pending implementation in a follow-up issue."

echo ""
echo "Done"
