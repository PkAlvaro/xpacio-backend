#!/usr/bin/env bash
# Backup PostgreSQL → MinIO. Run daily via cron or manually.
# Usage: ./scripts/backup.sh [/path/to/.env.prod]
set -euo pipefail

ENV_FILE="${1:-/home/deploy/xpacio/xpacio-backend/.env.prod}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

# Load env vars
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/xpacio_backup_${TIMESTAMP}.sql.gz"
MINIO_DEST="backups/postgres/${TIMESTAMP}.sql.gz"
CONTAINER="xpacio-backend-db-1"

echo "=== Backup PostgreSQL → $BACKUP_FILE ==="
docker exec "$CONTAINER" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-password \
  | gzip > "$BACKUP_FILE"

BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "Backup size: $BACKUP_SIZE"

# Upload to MinIO using mc (MinIO Client) if available, else boto3 python script
if command -v mc &>/dev/null; then
  echo "=== Upload via mc ==="
  mc alias set xpacio "http://${MINIO_ENDPOINT}" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" --quiet
  mc cp "$BACKUP_FILE" "xpacio/backups/postgres/${TIMESTAMP}.sql.gz"
else
  echo "=== Upload via Python/boto3 ==="
  python3 - <<PYEOF
import boto3, os, sys
from botocore.client import Config

s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{os.environ['MINIO_ENDPOINT']}",
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)

bucket = os.environ.get("MINIO_BUCKET", "xpacio-spaces")

# Ensure backups bucket exists
try:
    s3.head_bucket(Bucket="xpacio-backups")
except Exception:
    s3.create_bucket(Bucket="xpacio-backups")

s3.upload_file("$BACKUP_FILE", "xpacio-backups", "$MINIO_DEST")
print(f"Uploaded to xpacio-backups/$MINIO_DEST")
PYEOF
fi

# Keep only last 14 days locally
find /tmp -name "xpacio_backup_*.sql.gz" -mtime +1 -delete 2>/dev/null || true

echo "=== Backup completo: $TIMESTAMP ==="
