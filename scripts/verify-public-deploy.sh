#!/usr/bin/env bash
set -euo pipefail

# GET-only public (or local) deploy check. Never POST /v1/heatmap or analysis jobs.

WEB_BASE="${WEB_PUBLIC_URL:-}"
API_BASE="${API_PUBLIC_URL:-}"

if [[ -z "${WEB_BASE}" || -z "${API_BASE}" ]]; then
  echo "Set WEB_PUBLIC_URL and API_PUBLIC_URL (no trailing slash)." >&2
  exit 2
fi

WEB_BASE="${WEB_BASE%/}"
API_BASE="${API_BASE%/}"

fail() {
  echo "verify-public-deploy FAILED: $*" >&2
  exit 1
}

check_json() {
  local url="$1"
  local needle="$2"
  local body
  body="$(curl -sfS --max-time 20 "${url}")" || fail "GET ${url}"
  echo "${body}" | grep -q "${needle}" || fail "${url} missing ${needle}: ${body}"
  echo "ok ${url} -> ${body}"
}

check_json "${API_BASE}/health" '"status":"ok"'
check_json "${API_BASE}/ready" '"status":"ready"'
check_json "${WEB_BASE}/health" '"status":"ok"'
check_json "${WEB_BASE}/ready" '"status":"ready"'

ready_body="$(curl -sfS --max-time 20 "${API_BASE}/ready")"
echo "${ready_body}" | grep -q '"data_mode":"replay"' || fail "API /ready data_mode is not replay: ${ready_body}"

web_ready="$(curl -sfS --max-time 20 "${WEB_BASE}/ready")"
echo "${web_ready}" | grep -q '"data_mode":"replay"' || fail "WEB /ready data_mode is not replay: ${web_ready}"

job_url="${WEB_BASE}/api/v1/analysis/jobs/m0-probe"
job_body="$(curl -sfS --max-time 20 "${job_url}")" || fail "GET ${job_url}"
echo "${job_body}" | grep -q '"status":"unknown_job"' || fail "frontend→API job probe: ${job_body}"
echo "ok ${job_url} -> ${job_body}"

html="$(curl -sfS --max-time 20 "${WEB_BASE}/")" || fail "GET ${WEB_BASE}/"
echo "${html}" | grep -qi "<html" || fail "frontend root is not HTML"

echo "verify-public-deploy ok (GET /health /ready /api/v1/analysis/jobs/m0-probe only; zero heatmap POSTs)"
