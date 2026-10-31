#!/usr/bin/env bash
# Startet DBHub (MCP) gegen die lokale Dev-Datenbank – nur lesend.
# Voraussetzung: `make dev-services` läuft (DB-Port 127.0.0.1:3306 aus compose.dev.yaml).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
password_file="$root/secrets/db_password.txt"

if [[ ! -f "$password_file" ]]; then
  echo "secrets/db_password.txt fehlt – zuerst 'make secrets' ausführen." >&2
  exit 1
fi

# DSN per Umgebungsvariable statt Argument, damit das Passwort nicht in der Prozessliste steht.
DSN="mariadb://app:$(<"$password_file")@127.0.0.1:3306/appdb"
export DSN
exec npx -y @bytebase/dbhub@latest --transport stdio --readonly
