#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE_URL:-http://127.0.0.1:8000}"

for _ in $(seq 1 30); do
  if curl -sf "${API_BASE}/health" >/dev/null; then
    break
  fi
  sleep 1
done

curl -sf "${API_BASE}/health" | grep -q '"status":"ok"'
curl -sf "${API_BASE}/ready" | grep -q '"status":"ready"'

echo "smoke ok: ${API_BASE}/health and ${API_BASE}/ready"
