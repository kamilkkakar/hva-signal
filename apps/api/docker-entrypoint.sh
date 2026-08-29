#!/bin/sh
set -e
# Replay is the only deploy/smoke data mode. Do not default to live.
export DATA_MODE="${DATA_MODE:-replay}"
if [ -n "${RENDER_EXTERNAL_URL:-}" ] && [ -z "${API_PUBLIC_URL:-}" ]; then
  export API_PUBLIC_URL="${RENDER_EXTERNAL_URL}"
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
