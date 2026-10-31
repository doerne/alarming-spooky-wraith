# alarming-spooky-wraith

Vite + React + shadcn/ui · FastAPI · MariaDB · Docker – nach Clean Architecture und mit gehärteten Containern.
Angelegt mit dem Claude-Code-Plugin `fullstack-standards`.

## Voraussetzungen

Docker mit Compose v2 · [uv](https://docs.astral.sh/uv/) · Node.js 22 · Claude Code mit Plugin `fullstack-standards`

## Start

```bash
make setup    # Passwörter erzeugen, Abhängigkeiten installieren
make check    # alles prüfen
make dev      # DB + Backend in Docker, Frontend auf http://localhost:5173
make up       # gehärteter Stack auf http://localhost:8080
make help     # alle Befehle
```

## Struktur

```
backend/app/
  domain/          Entities, Fehler, Repository-Ports – ohne Framework
  application/     Use Cases + UnitOfWork-Port
  infrastructure/  SQLAlchemy, MariaDB, Settings
  presentation/    FastAPI-Router, DTOs, Fehler-Mapping
  main.py          Composition Root
frontend/src/
  app/             Layout, Provider, Startseite
  features/<name>/ model · api · hooks · components · index.ts
  shared/          ui (shadcn) · components · hooks · lib · api
```

Regeln für Architektur, Code, UI, Test-IDs und Container: siehe `CLAUDE.md`.
`make check` setzt sie automatisch durch.
