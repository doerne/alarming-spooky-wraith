#!/usr/bin/env bash
# Übernimmt eine neu erzeugte SBOM nur, wenn sie sich inhaltlich von der vorhandenen unterscheidet.
# Aufruf: sbom-update.sh <neue-datei> <ziel-datei>
set -euo pipefail

new_file="$1"
target_file="$2"
normalize="$(dirname "$0")/sbom-normalize.jq"

if [[ -f "$target_file" ]] && cmp -s \
  <(jq -S -f "$normalize" "$new_file") \
  <(jq -S -f "$normalize" "$target_file"); then
  echo "unverändert: $target_file"
  exit 0
fi

mkdir -p "$(dirname "$target_file")"
cp "$new_file" "$target_file"
echo "aktualisiert: $target_file"
