#!/bin/bash
set -e

echo "=== Xpacio Deploy ==="

git pull origin develop

docker compose -f docker-compose.prod.yml build --no-cache

docker compose -f docker-compose.prod.yml up -d --force-recreate

echo "=== Deploy completo ==="
docker compose -f docker-compose.prod.yml ps
