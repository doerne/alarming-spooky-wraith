#!/usr/bin/env bash
# Verbietet Tailwind-Palettenfarben außerhalb von shared/ui.
# Erlaubt sind nur die semantischen Tokens aus src/index.css (bg-primary, text-muted-foreground …).
set -euo pipefail
cd "$(dirname "$0")/.."

palette='slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose'
regex="\\b(bg|text|border|ring|outline|fill|stroke|from|via|to|divide|shadow|decoration|accent|caret)-(${palette})-[0-9]{2,3}\\b|\\b(bg|text|border)-(black|white)\\b"

if grep -rEn "$regex" src --include='*.tsx' --include='*.ts' --exclude-dir=ui; then
  echo "✗ Palettenfarben gefunden. Bitte semantische Tokens aus dem Theme verwenden." >&2
  exit 1
fi
echo "✓ Nur semantische Farben"
