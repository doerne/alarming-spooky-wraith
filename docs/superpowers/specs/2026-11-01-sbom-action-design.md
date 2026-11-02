# SBOM per GitHub Action – Design (kurz)

Stand: 2026-11-01

## Absicht
Eine GitHub Action erzeugt für CVE-Radar Software-Stücklisten (SBOM) nach CycloneDX und
speichert sie im Repo, damit jederzeit nachvollziehbar ist, welche Komponenten in welcher
Version enthalten sind – im Code und in den Docker-Images.

## Entscheidungen des Nutzers
- Umfang: Code-Abhängigkeiten **und** Docker-Images (Basis-Image, OS-Pakete).
- Auslöser: Push auf `main` mit Änderungen an Lockfiles, Dockerfiles oder `compose.yaml`;
  manuell (`workflow_dispatch`); wöchentlich (`schedule`).
- Werkzeug: **Trivy** für alles (passt zum Haus-Stack).

## Ergebnis
`sbom/` mit vier Dateien, CycloneDX JSON (Trivy schreibt Spezifikation 1.7):
| Datei | Quelle |
|---|---|
| `backend-source.cdx.json` | `trivy fs` auf `backend/` (uv.lock) |
| `frontend-source.cdx.json` | `trivy fs` auf `frontend/` (package-lock.json) |
| `backend-image.cdx.json` | `trivy image` auf das in der Action gebaute Backend-Image |
| `frontend-image.cdx.json` | `trivy image` auf das gebaute Frontend-Image |

## Meine Festlegungen
- Actions auf Commit-SHA gepinnt (Tag als Kommentar), Trivy-Version fest.
- Rechte: Workflow-Standard `contents: read`. Zwei Jobs: `generate` (nur Lesen, kein gespeichertes
  Token) erzeugt die SBOMs als Artefakt; nur `commit` bekommt `contents: write` und läuft auf `main`
  oder bei manuellem Start (dann auf den gewählten Branch).
- Commit nur bei inhaltlicher Änderung; Zeitstempel, Seriennummer, UUID-Referenzen und
  Image-/Layer-Hashes werden vor dem Vergleich normalisiert, damit nicht jeder Lauf einen Commit erzeugt.
- Commit-Autor `github-actions[bot]`, Nachricht `chore: update SBOM`; Commits über
  `GITHUB_TOKEN` lösen ohnehin keinen weiteren Lauf aus.
- Images werden nur lokal in der Action gebaut (kein Push in eine Registry).
- Kein `git push --force`; vor dem Push `git pull --rebase`. Wird `main` später geschützt, braucht der
  Commit-Job eine Ausnahme oder einen PR-Weg.
- Kurze Beschreibung in `sbom/README.md` und in `docs/local-development.md`.

## Nicht-Ziele
Schwachstellen-Scan der SBOM, Signieren/Attestieren, Upload in Dependency-Track,
Einspielen ins CVE-Radar-Inventar (wäre ein spannender nächster Schritt).

## Prüfung
`actionlint` lokal (falls verfügbar, sonst per Docker), die Trivy-Befehle einmal lokal gegen
die Lockfiles laufen lassen (Images lokal nicht baubar – kein buildx); erster echter Lauf
per `workflow_dispatch` auf einem Branch.
