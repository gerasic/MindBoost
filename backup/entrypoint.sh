#!/usr/bin/env bash
set -euo pipefail

echo "${BACKUP_INTERVAL_CRON} /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1" > /etc/crontabs/root

exec crond -f -l 2
