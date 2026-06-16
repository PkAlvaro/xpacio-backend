#!/usr/bin/env bash
# Install cron jobs on the production droplet (run once as deploy user).
# Usage: ssh deploy@165.227.181.241 'bash /home/deploy/xpacio/xpacio-backend/scripts/setup_cron.sh'
set -euo pipefail

REPO="/home/deploy/xpacio/xpacio-backend"
BACKUP_SCRIPT="$REPO/scripts/backup.sh"
LOG_DIR="/home/deploy/logs"

mkdir -p "$LOG_DIR"
chmod +x "$BACKUP_SCRIPT"

# Build crontab: backup daily at 03:00, log rotation weekly
CRON_ENTRY="0 3 * * * $BACKUP_SCRIPT >> $LOG_DIR/backup.log 2>&1"
LOG_ROTATE="0 0 * * 0 find $LOG_DIR -name '*.log' -size +50M -exec truncate -s 10M {} \;"

(crontab -l 2>/dev/null | grep -v "backup.sh" | grep -v "truncate.*logs"; echo "$CRON_ENTRY"; echo "$LOG_ROTATE") | crontab -

echo "Cron instalado:"
crontab -l
