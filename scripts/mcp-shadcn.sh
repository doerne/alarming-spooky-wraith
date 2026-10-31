#!/usr/bin/env bash
# Startet den shadcn-MCP-Server im Frontend-Ordner, damit er components.json findet.
set -euo pipefail
cd "$(dirname "$0")/../frontend"
exec npx -y shadcn@latest mcp
