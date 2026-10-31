#!/usr/bin/env bash
# Erzeugt zufällige DB-Passwörter als Docker Secrets. Bestehende Dateien bleiben unverändert.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p secrets
# Das Verzeichnis schützt die Dateien auf dem Host. Die Dateien selbst müssen
# lesbar sein, weil Compose sie ohne Swarm 1:1 in die Container einbindet und
# die Container nicht als root laufen.
chmod 700 secrets

generate() {
  local file="secrets/$1.txt"
  if [[ -f "$file" ]]; then
    echo "• $file existiert bereits"
    return
  fi
  local value
  # "|| true": tr endet mit SIGPIPE, sobald head genug Zeichen hat
  value=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 40 || true)
  if [[ ${#value} -ne 40 ]]; then
    echo "✗ Konnte kein Passwort für $file erzeugen" >&2
    exit 1
  fi
  printf '%s' "$value" >"$file"
  chmod 644 "$file"
  echo "✓ $file erzeugt"
}

generate db_password
generate db_root_password
