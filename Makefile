SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE     := docker compose -f compose.yaml
COMPOSE_DEV := $(COMPOSE) -f compose.dev.yaml

.PHONY: help setup secrets claude-setup dev dev-services up down ps logs migrate \
        check check-backend check-frontend check-docker test scan

help: ## Diese Hilfe
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ------------------------------------------------------------------- Setup
setup: secrets ## Abhängigkeiten installieren und Lockfiles erzeugen
	chmod +x scripts/*.sh frontend/scripts/*.sh
	@if compgen -G ".claude/hooks/*.sh" >/dev/null; then chmod +x .claude/hooks/*.sh; fi
	cd backend && uv sync
	cd frontend && npm install

secrets: ## Zufällige DB-Passwörter erzeugen (falls nicht vorhanden)
	@./scripts/generate-secrets.sh

claude-setup: ## Plugins, Context7 und shadcn-Skill für Claude Code einrichten
	./scripts/setup-claude.sh

# --------------------------------------------------------------- Betrieb
dev-services: secrets ## DB + Backend in Docker, Ports nur auf 127.0.0.1
	$(COMPOSE_DEV) up -d --build db migrate backend

dev: dev-services ## Docker-Dienste + Vite-Dev-Server (http://localhost:5173)
	cd frontend && npm run dev

up: secrets ## Gehärteten Stack bauen und starten (http://localhost:8080)
	$(COMPOSE) up -d --build

down: ## Stack stoppen – die Datenbank bleibt erhalten
	$(COMPOSE_DEV) down

ps: ## Status der Container
	$(COMPOSE_DEV) ps

logs: ## Logs verfolgen
	$(COMPOSE_DEV) logs -f --tail=100

migrate: ## Alembic-Migrationen gegen die laufende DB anwenden
	$(COMPOSE_DEV) run --rm --build migrate

# --------------------------------------------------------------- Qualität
check: check-backend check-frontend check-docker ## Alle Prüfungen (nutzt auch der Stop-Hook)

check-backend: ## ruff, mypy strict, import-linter, pytest
	cd backend && uv run ruff format --check . && uv run ruff check . && \
	  uv run mypy && uv run lint-imports && uv run pytest -q

check-frontend: ## tsc, ESLint (Test-IDs, Architektur), Palette-Check, Vitest
	cd frontend && npx tsc -b && npx eslint --max-warnings 0 . && \
	  ./scripts/check-palette.sh && npx vitest run

check-docker: secrets ## hadolint + Compose-Validierung
	@for f in backend/Dockerfile frontend/Dockerfile; do \
	  echo "hadolint $$f"; \
	  if command -v hadolint >/dev/null; then hadolint "$$f"; \
	  else docker run --rm -i -v "$(CURDIR)/.hadolint.yaml:/.hadolint.yaml:ro" hadolint/hadolint < "$$f"; \
	  fi || exit 1; \
	done
	$(COMPOSE) config --quiet
	$(COMPOSE_DEV) config --quiet

test: ## Nur die Tests
	cd backend && uv run pytest -q
	cd frontend && npx vitest run

scan: ## Images mit Trivy auf HIGH/CRITICAL-Schwachstellen prüfen
	$(COMPOSE) build backend frontend
	@for img in $$($(COMPOSE) config --images | grep -E 'backend|frontend'); do \
	  echo "trivy $$img"; \
	  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest \
	    image --severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed "$$img" || exit 1; \
	done
