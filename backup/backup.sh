#!/usr/bin/env bash
set -euo pipefail

mkdir -p /backups

TS=$(date +'%Y%m%d%H%M%S')

PGPASSWORD="$DB_PASSWORD" \
  pg_dump \
    --host "$DB_HOST" \
    --username "$DB_USER" \
    --dbname "$DB_NAME" \
  > "/backups/${TS}.sql"

cd /backups
ls -1tr *.sql | head -n -"$BACKUP_RETENTION_COUNT" | xargs --no-run-if-empty rm -f
