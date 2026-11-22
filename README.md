# CVE-Radar (alarming-spooky-wraith)

CVE-Radar zeigt, welche bekannten Schwachstellen (CVEs) die Komponenten unserer Anwendungen
betreffen – versionsgenau, nach Risiko sortiert und mit Herkunftsnachweis. Treffer lassen sich
im Tool bewerten, als Issues exportieren oder direkt mit GitHub abgleichen.

Vite + React + shadcn/ui · FastAPI · MariaDB · Docker – nach Clean Architecture und mit
gehärteten Containern. Angelegt mit dem Claude-Code-Plugin `fullstack-standards`.

## Funktionen

| Bereich | Was es kann |
|---|---|
| **Inventar** | Anwendungen und ihre Komponenten (Sprache, Framework, Library, Dienst) mit Version pflegen – von Hand oder per CycloneDX-SBOM-Upload mit Versionsverlauf |
| **Schwachstellen** | Alle Treffer in einer Tabelle, nach Risk Score sortiert, mit Spaltenfiltern, Detailansicht und Statusänderung |
| **Quellen** | CVE-Quellen ein- und ausschalten, API-Keys hinterlegen, Fortschritt des Scans je Quelle sehen |
| **Export für KI** | Offene CVEs einer Anwendung als Markdown mit fertigen Issue-Texten für einen Agenten |
| **Rückkanal** | Agenten melden Issue-Link und Status per API; „behoben“ wird mit der nächsten SBOM überprüft |
| **GitHub** | Issues im Repo der Anwendung anlegen (per Button oder automatisch) und den Status in beide Richtungen abgleichen |

## Schnellstart

Voraussetzungen: Docker mit Compose v2 **und `buildx`** · [uv](https://docs.astral.sh/uv/) ·
Node.js 22 · Claude Code mit Plugin `fullstack-standards`

```bash
make setup    # Passwörter erzeugen, Abhängigkeiten installieren
make check    # alles prüfen
make dev      # DB + Backend in Docker, Frontend auf http://localhost:5173
make up       # gehärteter Stack auf http://localhost:8080
make help     # alle Befehle
```

Danach: unter **Inventar** eine Anwendung anlegen, Komponenten eintragen oder eine SBOM
hochladen, dann unter **Schwachstellen** *Scan starten*. Die Treffer erscheinen dort, den
Fortschritt je Quelle zeigt **Quellen**.

Ausführliche Anleitung, Notweg ohne `buildx` und Migrationen:
[`docs/local-development.md`](docs/local-development.md).

## Konfiguration

Das Backend liest Umgebungsvariablen (`backend/app/infrastructure/config.py`). In Compose sind
alle Werte vorbelegt; nötig ist höchstens `GITHUB_APP_ID`.

| Variable | Standard | Zweck |
|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` | `db`, `3306`, `appdb`, `app` | Datenbankverbindung |
| `DB_PASSWORD_FILE` | `/run/secrets/db_password` | DB-Passwort als Docker Secret |
| `DATABASE_URL` | – | Ersetzt die Einzelwerte (nur Notweg ohne Docker) |
| `OKF_ROOT` | `/data/okf` | Ablage der Advisory-Dateien (Volume `okfdata`) |
| `SOURCE_CACHE_ROOT` | `/data/sources` | Cache für große Quellen-Abzüge (Volume `sourcecache`) |
| `OSV_BASE_URL` | `https://api.osv.dev` | OSV-API |
| `ENABLE_DOCS` | `false` | Swagger-UI unter `/api/docs` (im Dev-Modus an) |
| `GITHUB_APP_ID` | – | ID der GitHub App; ohne sie ist GitHub „nicht konfiguriert“ |
| `GITHUB_APP_PRIVATE_KEY_FILE` | `/run/secrets/github_app_private_key` | Privater Schlüssel der App als Docker Secret |
| `GITHUB_API_URL` | `https://api.github.com` | GitHub-API (z. B. für GitHub Enterprise) |

Secrets liegen nur in `secrets/` und werden als Docker Secrets eingebunden;
`make secrets` (bzw. `scripts/generate-secrets.sh`) legt fehlende Dateien an.
API-Keys der CVE-Quellen werden in der Oberfläche hinterlegt und in der Datenbank gespeichert –
eine bewusste Ausnahme, begründet in
[`docs/superpowers/specs/2026-11-01-cve-sources-design.md`](docs/superpowers/specs/2026-11-01-cve-sources-design.md).

## Datenquellen

Ein Scan fragt alle aktiven Quellen ab und führt ihre Meldungen zusammen. Advisories, die
sich über Aliase (CVE-, GHSA-, PYSEC-ID …) als dieselbe Lücke erweisen, werden zu einer
zusammengelegt.

- **Ohne Key:** OSV.dev, EUVD, CVE.org, die Sprach-Datenbanken (PyPA, Go, RustSec, Ruby
  Advisory DB, Packagist, Haskell, R, opam) und Framework-Quellen.
- **Optionaler Key** (höheres Rate-Limit): GitHub Advisory Database, Symfony, Laravel, NVD.
- **Pflicht-Key:** Snyk, Sonatype OSS Index, CVEdetails – ohne Key übersprungen.

Versionsgenau abgeglichen werden Pakete der Ökosysteme npm, PyPI, Go, crates.io, RubyGems,
Packagist, Maven, NuGet, Hackage, CRAN und opam. Jede Advisory wird zusätzlich als
menschenlesbare OKF-Datei (Markdown + YAML-Frontmatter) mit Quellenangabe abgelegt; die
Datenbank ist der Index. Welche Felder gespeichert und welche verworfen werden:
[`docs/cve-data-retention.md`](docs/cve-data-retention.md).

Scans laufen im Hintergrund und werden derzeit **manuell** gestartet (*Scan starten* auf der
Schwachstellen-Seite oder `POST /api/ingest/run`); einen Zeitplan gibt es noch nicht.

## Risk Score

Jeder Treffer bekommt einen Wert von 0 bis 100 und eine Stufe
(`backend/app/application/risk_score.py`):

- **Wert** = CVSS-Basisscore × 10, gerundet. Ohne CVSS bleibt er 0 – geraten wird nicht.
- **Stufen:** ≥ 90 kritisch · 70–89 hoch · 40–69 mittel · < 40 niedrig.
- Die Begründung steht in der Detailansicht und in der OKF-Datei.

EPSS, CISA KEV, Fix-Verfügbarkeit und direkt/transitiv fließen noch nicht ein (Stufe 3 der
Roadmap in [`docs/superpowers/specs/2026-10-31-cve-radar-design.md`](docs/superpowers/specs/2026-10-31-cve-radar-design.md)).

## Treffer bearbeiten

Status: `offen` · `in_arbeit` · `akzeptiert` · `false_positive` · `behoben`.

- **Von Hand** in der Schwachstellen-Tabelle oder in der Detailansicht, mit Kommentar.
- **Über die SBOM:** Fällt eine betroffene Komponente aus einer neuen SBOM-Version heraus,
  markiert der nächste Scan ihre Treffer als behoben – oder überträgt den Status auf die neue
  Version, wenn die Lücke dort weiter besteht.
- **Über die API:** Ein Agent meldet Issue-Link oder Status per
  `PATCH /api/applications/{id}/cves/{advisoryId}`. Ein so gemeldetes „behoben“ ist vorläufig:
  enthält die nächste SBOM die Komponente unverändert, wird der Treffer wieder offen.
- **Über GitHub:** Ein geschlossenes Issue macht offene Treffer zu „behoben“ (als
  `not_planned` geschlossen: „akzeptiert“); öffnet CVE-Radar einen Treffer wieder, öffnet es
  auch das Issue. Der Abgleich läuft nach jedem Scan und per Button.

Anleitungen zu SBOM-Upload, KI-Export und Einrichtung der GitHub App stehen in
[`docs/local-development.md`](docs/local-development.md).

## Struktur

```
backend/app/
  domain/          Entities, Fehler, Repository-Ports – ohne Framework
  application/     Use Cases + UnitOfWork-Port
  infrastructure/  SQLAlchemy, MariaDB, Settings, CVE-Quellen, GitHub-Adapter
  presentation/    FastAPI-Router, DTOs, Fehler-Mapping
  main.py          Composition Root
frontend/src/
  app/             Layout, Provider, Navigation
  features/        cves · inventory · sources (je model · api · hooks · components · index.ts)
  shared/          ui (shadcn) · components · hooks · lib · api
docs/
  local-development.md   Betrieb, Quellen, SBOM, Export, GitHub
  superpowers/           Designs (specs/) und Umsetzungspläne (plans/) je Vorhaben
```

Regeln für Architektur, Code, UI, Test-IDs und Container: siehe `CLAUDE.md`.
`make check` setzt sie automatisch durch.
