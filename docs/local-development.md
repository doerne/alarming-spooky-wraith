# Lokale Entwicklungsumgebung starten

Diese Anleitung beschreibt den normalen (vorgesehenen) Weg über Docker Compose
und einen Notweg ohne Image-Build, falls `buildx` fehlt.

## Voraussetzungen

- **Docker** mit **Compose v2 und `buildx`.**
  Die Dockerfiles nutzen BuildKit-Features (`RUN --mount=type=cache`); ohne
  `buildx` schlägt jeder Image-Build fehl
  (`BuildKit is enabled but the buildx component is missing`).
  Prüfen: `docker buildx version`. Fehlt es, das Paket `docker-buildx`
  (bzw. `docker-buildx-plugin`) der Distribution installieren.
- **[uv](https://docs.astral.sh/uv/)** für das Python-Backend.
- **Node.js 22** für das Frontend.

## Einmalig einrichten

```bash
make setup    # erzeugt DB-Passwörter (secrets/), installiert Backend- und Frontend-Abhängigkeiten
```

## Normaler Weg (Docker Compose)

```bash
make dev
```

`make dev` startet zuerst `make dev-services` – Datenbank, Migration und Backend
laufen in Docker, Ports nur auf `127.0.0.1` – und danach den Vite-Dev-Server.

| Dienst | Adresse |
|---|---|
| Frontend (Vite, Hot Reload) | http://localhost:5173 |
| Backend-API | http://127.0.0.1:8000/api |
| Swagger-UI (nur im Dev-Modus) | http://127.0.0.1:8000/api/docs |
| MariaDB (für lokale Tools/DBHub) | `127.0.0.1:3306` |

Nur die Docker-Dienste ohne Frontend:

```bash
make dev-services                 # DB + Backend in Docker
cd frontend && npm run dev        # Frontend separat
```

Der Vite-Dev-Server leitet `/api` automatisch an `127.0.0.1:8000` weiter
(siehe `frontend/vite.config.ts`).

### Gehärteter Gesamt-Stack (produktionsnah)

```bash
make up        # alles in Docker, Frontend über nginx auf http://localhost:8080
```

## Datenbank-Migrationen

```bash
cd backend && uv run alembic revision --autogenerate -m "beschreibung"
make migrate   # wendet die Migrationen gegen die laufende DB an
```

## Prüfen

```bash
make check     # ruff, mypy, import-linter, pytest, tsc, ESLint, Palette, Vitest, hadolint, compose
```

## Stoppen

```bash
make down      # stoppt den Stack; das Datenbank-Volume bleibt erhalten
```

> **Nie** `docker compose down -v` ausführen – das löscht die Datenbank.

## Nützliche Befehle

```bash
make help      # alle Make-Ziele
make ps        # Status der Container
make logs      # Logs verfolgen
```

---

## Notweg ohne `buildx` (kein Image-Build möglich)

Wenn `buildx` nicht installiert werden kann, lassen sich die App-Images nicht
bauen. Dann die **Datenbank im Container** betreiben und **Backend und Frontend
aus dem Quellcode** auf dem Host starten. Das ist nur für die lokale Erprobung
gedacht, nicht gehärtet und nicht der echte Stack.

```bash
# 1) MariaDB als Wegwerf-Container (eigenes Passwort, Port 3307, um 3306 nicht zu stören)
docker run -d --name asw-devdb \
  -e MARIADB_DATABASE=appdb -e MARIADB_USER=app -e MARIADB_PASSWORD=devtest \
  -e MARIADB_ROOT_PASSWORD=devroot \
  -p 127.0.0.1:3307:3306 mariadb:11.4

# 2) Schema anlegen (warten bis die DB bereit ist, dann migrieren)
cd backend
export DATABASE_URL="mariadb+pymysql://app:devtest@127.0.0.1:3307/appdb?charset=utf8mb4"
export OKF_ROOT="$PWD/../.okf-dev"     # beschreibbares Verzeichnis für die OKF-Files
export SOURCE_CACHE_ROOT="$PWD/../.sources-dev"  # Cache für Quellen-Abzüge
uv run alembic upgrade head

# 3) Backend starten (eigenes Terminal)
ENABLE_DOCS=true uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

# 4) Frontend starten (eigenes Terminal)
cd frontend && npm run dev
```

Aufräumen:

```bash
docker rm -f asw-devdb     # Wegwerf-DB entfernen
```

Gegenüber dem normalen Weg entfällt hier die Container-Härtung; `DATABASE_URL`
und `OKF_ROOT` werden per Umgebungsvariable gesetzt statt über Docker-Secrets
und Volumes. Sobald `buildx` verfügbar ist, ist `make dev` der richtige Weg.

## Quellen und API-Keys

Die Seite **Quellen** listet alle CVE-Quellen, die im Code eingebaut sind
(`backend/app/infrastructure/sources/catalog.py`). Jede Quelle lässt sich dort
aktivieren oder deaktivieren; der Scan fragt nur aktive Quellen ab.

- **Ohne Key:** OSV.dev, EUVD, CVE.org, alle Sprach-Datenbanken (PyPA, Go, RustSec,
  Ruby Advisory DB, Packagist, Haskell, R, opam) und die Framework-Quellen.
- **Optionaler Key** (hebt nur das Rate-Limit): GitHub Advisory Database, Symfony,
  Laravel (GitHub-Token) und NVD (NVD-API-Key).
- **Pflicht-Key:** Snyk (`<org-id>:<token>`), Sonatype OSS Index
  (`<benutzer>:<token>`) und CVEdetails (API-Token). Ohne Key werden sie beim Scan
  übersprungen.

Keys werden auf der Quellen-Seite hinterlegt und **unverschlüsselt in der Datenbank**
gespeichert (bewusste Ausnahme vom Secret-Standard, siehe
`docs/superpowers/specs/2026-11-01-cve-sources-design.md` §4). Die API gibt einen
gespeicherten Key nie zurück.

Der Scan läuft im Hintergrund; „Scan starten“ kehrt sofort zurück, die Quellen-Seite
zeigt pro Quelle den Fortschritt. Große Abzüge (CVE.org rund 650 MB, OSV-Dumps)
werden im Volume `sourcecache` (`/data/sources`) zwischengespeichert. Im Notweg ohne
`buildx` dafür `SOURCE_CACHE_ROOT` auf ein beschreibbares Verzeichnis setzen.

## Software-Stückliste (SBOM)

Der Workflow `.github/workflows/sbom.yml` erzeugt mit Trivy CycloneDX-SBOMs für Backend und
Frontend – aus den Lockfiles und aus den gebauten Docker-Images – und speichert sie unter
`sbom/` (Details in `sbom/README.md`). Manuell starten: *Actions → SBOM → Run workflow*.
Lokal geht dasselbe ohne Installation per Container (`aquasec/trivy` in der Version, die in
`sbom.yml` unter `TRIVY_VERSION` steht):

```bash
docker run --rm -v "$PWD/backend:/src:ro" aquasec/trivy:<TRIVY_VERSION ohne v> fs --format cyclonedx /src
```
