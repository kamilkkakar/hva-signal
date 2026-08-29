#!/bin/sh
set -e
export PORT="${PORT:-80}"
raw="${API_UPSTREAM:-api:8000}"
raw="${raw%/}"
case "$raw" in
  https://*|http://*)
    ;;
  *)
    raw="http://${raw}"
    ;;
esac
export API_UPSTREAM="$raw"
host="${raw#http://}"
host="${host#https://}"
host="${host%%/*}"
host="${host##*@}"
host="${host%%:*}"
export API_UPSTREAM_HOST="$host"
envsubst '${PORT} ${API_UPSTREAM} ${API_UPSTREAM_HOST}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf
if [ "${NGINX_DRY_RUN:-}" = "1" ]; then
  nginx -t
  cat /etc/nginx/conf.d/default.conf
  exit 0
fi
exec nginx -g 'daemon off;'
