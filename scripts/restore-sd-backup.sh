#!/usr/bin/env bash
set -euo pipefail

BAK_PATH="${1:-/Users/laurenross/Downloads/InstitutVajraYogini_20260707_0123.bak}"
CONTAINER=ivy-sqlserver
SA_PASSWORD='IvyDash2026!'

echo "=== IVY SeminarDesk SQL Backup Restore ==="

if ! docker info &>/dev/null; then
  echo "Error: Docker is not running" >&2; exit 1
fi

if [ ! -f "$BAK_PATH" ]; then
  echo "Error: Backup not found at $BAK_PATH" >&2; exit 1
fi

BAK_DIR=$(dirname "$BAK_PATH")
BAK_FILE=$(basename "$BAK_PATH")

docker stop $CONTAINER 2>/dev/null || true
docker rm $CONTAINER 2>/dev/null || true

echo "Starting SQL Server container..."
docker run -d --name $CONTAINER --platform linux/amd64 \
  -e 'ACCEPT_EULA=Y' \
  -e "MSSQL_SA_PASSWORD=$SA_PASSWORD" \
  -p 1433:1433 \
  -v "$BAK_DIR:/backup" \
  mcr.microsoft.com/mssql/server:2022-latest

echo "Waiting for SQL Server startup..."
sleep 15

SQLCMD="docker exec $CONTAINER /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P $SA_PASSWORD -C"

$SQLCMD -Q "SELECT 1" >/dev/null || { echo "SQL Server not ready"; exit 1; }

echo "Restoring database from $BAK_FILE..."
$SQLCMD -Q "
RESTORE DATABASE IvySD
FROM DISK = '/backup/$BAK_FILE'
WITH MOVE 'BerndBosbach' TO '/var/opt/mssql/data/IvySD.mdf',
     MOVE 'BerndBosbach_log' TO '/var/opt/mssql/data/IvySD_log.ldf',
     REPLACE
"

echo "=== Restore complete ==="
echo "Connect: sqlcmd -S localhost -U sa -P '$SA_PASSWORD' -C -d IvySD"
echo "Or run: python3 bak_extract.py"
