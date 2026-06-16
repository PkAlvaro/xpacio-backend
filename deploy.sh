#!/usr/bin/env bash
# Deploy Xpacio to production droplet.
# Usage: ./deploy.sh [--full]
#   --full   rebuild ALL services with no-cache (use after dependency changes)
set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
FULL=0
[[ "${1:-}" == "--full" ]] && FULL=1

echo "=== Xpacio Deploy $(date '+%Y-%m-%d %H:%M:%S') ==="

git pull origin develop

if [ "$FULL" -eq 1 ]; then
  echo "--- Full rebuild (no-cache) ---"
  $COMPOSE build --no-cache
else
  echo "--- Incremental build ---"
  $COMPOSE build frontend api worker beat
fi

echo "--- Rolling restart ---"
$COMPOSE up -d --no-deps frontend api worker beat

echo "--- Waiting for API health ---"
for i in $(seq 1 18); do
  STATUS=$($COMPOSE ps api --format json 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['Health'] if d else 'unknown')" 2>/dev/null \
    || echo "unknown")
  if [ "$STATUS" = "healthy" ]; then
    echo "API healthy (${i}0s)"
    break
  fi
  if [ "$i" -eq 18 ]; then
    echo "ERROR: API never became healthy"
    $COMPOSE logs api --tail=80
    exit 1
  fi
  printf "."
  sleep 10
done

echo ""
echo "--- Reloading nginx (re-resolve upstream IPs) ---"
docker exec xpacio-backend-nginx-1 nginx -s reload 2>/dev/null || true

echo "=== Deploy completo ==="
$COMPOSE ps
