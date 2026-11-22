# GitHub-Anbindung – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (oder superpowers:subagent-driven-development). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CVE-Radar legt für offene CVEs einer Anwendung GitHub-Issues im Repo der Anwendung an (manuell per Button oder automatisch für neue Treffer) und gleicht Status zweiseitig ab, ohne dass sich Issue und CVE-Radar gegenseitig überschreiben.

**Architecture:** Port `IssueTracker` (domain) mit Adapter `GitHubAppIssueTracker` (httpx + PyJWT, infrastructure). Use Case `SyncGitHubIssues` (application) läuft nach dem Scan in eigener Unit of Work und per Button im Hintergrund über einen gemeinsamen Runner, der Scan und Abgleich nie gleichzeitig ausführt. Abgleich-Entscheidung als reine Funktion (Tabelle aus dem Spec), damit sie ohne Fakes-Infrastruktur testbar ist.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2, Alembic, httpx, PyJWT[crypto] (neu, freigegeben), React, TanStack Query, React Hook Form + zod, shadcn/ui.

**Spec:** `docs/superpowers/specs/2026-11-21-github-integration-design.md`

## Global Constraints
- Branch `sbom-action`; neue Abhängigkeit nur `PyJWT[crypto]` (freigegeben); sonst keine.
- Schlüssel (`/run/secrets/github_app_private_key`) nur im Adapter lesen; nie loggen, nie in API-Antworten.
- Komplexität ≤ 8, Python mypy strict, max. 5 Parameter; TS max. 4 Parameter, kein `any`.
- `make check` nach jeder Task; vor jedem Commit `fullstack-standards:architecture-reviewer`.
- Commits klein, `feat:` / `fix:` / `refactor:`, Co-Author-Zeile wie in den bisherigen Commits.
- Testdaten/Fakes: `tests/fakes.py`. Neue Fakes dort (`FakeIssueTracker`, `FakeIssueFormatter`).

## Review Focus
1. **GitHub nicht konfiguriert / App im Repo nicht installiert / Netzfehler** → Scan läuft unverändert durch; Fehlertext in `githubSyncMessage`; andere Anwendungen laufen weiter. Test in Task 4 und Task 6.
2. **Issue auf GitHub gelöscht (404 bei `get`)** → kein Absturz; Verknüpfung wird als „nicht mehr vorhanden“ vermerkt, `issue_url` bleibt unverändert, nichts wird geschlossen. Test in Task 3.
3. **Issue-Liste im Duplikat-Check über 100 Einträge** → Paginierung folgt Link-Header; ein Marker auf Seite 2 wird gefunden, es wird kein zweites Issue angelegt. Test in Task 5.
4. **Repo-Eingabe mit Zeilenumbruch, `..` oder Pfadzeichen** → 422, keine GitHub-Anfrage. Test in Task 6.
5. **Sync-Start während Scan läuft (und umgekehrt)** → 409, kein paralleles Anlegen. Test in Task 6.

---

### Task 1: Domain – Status, Port, Fehler, Anwendungsfelder

**Files:**
- Modify: `backend/app/domain/vulnerability.py` (`IssueState`, Finding-Felder `issue_state`, `first_seen_at`, Risiko-Rangfolge)
- Modify: `backend/app/domain/inventory.py` (`Application.github_repository`, `auto_issue_min_level`, `auto_issue_enabled_at`, `github_synced_at`, `github_sync_message`)
- Modify: `backend/app/domain/errors.py` (`IssueTrackerError(DomainError)`)
- Modify: `backend/app/domain/ports.py` (`TrackedIssue`, `IssueContent`, `IssueTracker`, `IssueFormatter`)
- Test: `backend/tests/unit/test_domain_model.py`, `backend/tests/unit/test_errors.py`

**Interfaces:**
- Consumes: bestehende `Severity`, `Finding`, `Application`, `DomainError`.
- Produces:
  - `class IssueState(StrEnum): OPEN = "open"; CLOSED = "closed"`
  - `def severity_rank(level: Severity) -> int` (niedrig 0 … kritisch 3)
  - `TrackedIssue(number: int, url: str, is_open: bool, not_planned: bool = False)` (frozen)
  - `IssueContent(title: str, body: str, labels: tuple[str, ...])` (frozen)
  - `IssueTracker`-Protocol: `is_configured() -> bool`, `existing_markers(repository) -> dict[str, TrackedIssue]`, `get(repository, number) -> TrackedIssue | None`, `create(repository, content: IssueContent) -> TrackedIssue`, `set_open(repository, number, is_open, comment, not_planned=False) -> None`
  - `IssueFormatter`-Protocol: `format(application_id: int, draft: IssueDraft) -> IssueContent`
  - `IssueTrackerError(message: str)`. **Festlegung:** `get` gibt bei 404 `None` zurück (Issue existiert nicht mehr).

- [ ] **Step 1: Failing tests** – `severity_rank` Reihenfolge (`niedrig < mittel < hoch < kritisch`); `Finding` hat `issue_state=None`, `first_seen_at=None` als Standard; `Application` hat `github_repository=None`, `auto_issue_min_level=None`, `github_sync_message=""`.
- [ ] **Step 2: Run** `cd backend && uv run pytest tests/unit/test_domain_model.py -v` → FAIL.
- [ ] **Step 3: Implementieren** (Felder mit Defaults, damit bestehende Konstruktoren unverändert bleiben).
- [ ] **Step 4: Run** → PASS; `uv run mypy` grün.
- [ ] **Step 5: Commit** `feat: add domain model for GitHub issue sync`

### Task 2: Persistenz – Migration, Modelle, Repositories

**Files:**
- Modify: `backend/app/infrastructure/models.py` (Spalten an `ApplicationRow`, `FindingRow`)
- Modify: `backend/app/infrastructure/repositories.py` (Mapping + `save_github_state`/`save_application_github` o. ä.)
- Modify: `backend/app/domain/ports.py` (`FindingRepository.save_issue_link(finding_id, issue_url, issue_state)`, `ApplicationRepository.update` falls fehlt)
- Create: Migration `backend/alembic/versions/<rev>_github_integration.py` (per `uv run alembic revision --autogenerate -m "github integration"`)
- Modify: `backend/tests/fakes.py` (Fake-Repositories ziehen nach)
- Test: `backend/tests/unit/test_repositories.py`, `backend/tests/unit/test_repositories_foreign_keys.py`

**Interfaces:**
- Consumes: Task 1 Felder.
- Produces: `FindingRepository.save_issue_link(finding_id: int, issue_url: str, issue_state: IssueState | None) -> None`; `ApplicationRepository.update(application: Application) -> Application`.

- [ ] **Step 1: Failing test** – Round-trip: Anwendung mit Repo und Schwelle speichern und lesen; Finding mit `issue_state=CLOSED`, `first_seen_at` speichern und lesen; Bestand (`first_seen_at` NULL) bleibt NULL.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Migration erzeugen** (`cd backend && uv run alembic revision --autogenerate -m "github integration"`), prüfen (Spalten nullable, Default NULL/leer), `make migrate`, `uv run alembic check`.
- [ ] **Step 4: Repos implementieren**; `first_seen_at` wird nur beim ersten Upsert gesetzt (bestehendes Finding behält Wert).
- [ ] **Step 5: Run** → PASS; `make check`.
- [ ] **Step 6: Commit** `feat: persist GitHub repository, issue state and first-seen time`

### Task 3: Abgleich-Entscheidung als reine Funktion

**Files:**
- Create: `backend/app/application/issue_sync_rules.py`
- Test: `backend/tests/unit/test_issue_sync_rules.py`

**Interfaces:**
- Consumes: `IssueState`, `TrackedIssue`, `FindingStatus`.
- Produces:
  - `class CveAggregate(StrEnum): OPEN = "offen"; RATED = "bewertet"; FIXED = "behoben"`
  - `def aggregate_state(findings: Sequence[Finding]) -> CveAggregate` (Gesamtzustand nach Spec; ausgebaute Treffer zählen mit `resolved_by`/Status)
  - `class IssueAction(StrEnum)`: `NONE`, `MARK_FIXED`, `MARK_ACCEPTED`, `MARK_CLOSED_EXTERNALLY_COMPLETED`, `CLOSE_COMPLETED`, `CLOSE_NOT_PLANNED`, `REOPEN`, `LINK_ONLY`
  - `def decide_issue_action(stored: IssueState | None, live: TrackedIssue, aggregate: CveAggregate, has_fix_evidence: bool) -> IssueAction`
  - `def is_missing_issue(...)` → nicht nötig; Fall „404“ wird im Use Case behandelt (Review Focus 2).

- [ ] **Step 1: Failing test** – parametrisiert über **alle Zeilen der Abgleich-Tabelle** im Spec (Zeilen „(keiner) → closed, completed / not_planned / open“, „open → closed …“, „closed → open“, „unverändert open“ mit/ohne SBOM-Nachweis, „unverändert closed → offen“, „sonst → NONE“). Dazu Aggregat-Tests: offen schlägt bewertet schlägt behoben; ausgebaute `behoben` zählt.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implementieren** – Verzweigung über Tabelle (Dict-Lookup statt Kaskade, Komplexität ≤ 8).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: decide GitHub issue status sync per the design table`

### Task 4: Use Case `SyncGitHubIssues` – Abgleich und Anlegen

**Files:**
- Create: `backend/app/application/github_sync.py`
- Modify: `backend/tests/fakes.py` (`FakeIssueTracker`, `FakeIssueFormatter`)
- Test: `backend/tests/unit/test_github_sync.py`

**Interfaces:**
- Consumes: Task 1 Port, Task 3 Regeln, `ExportApplicationIssues` (bestehend), `UnitOfWork`, `Clock`.
- Produces:
  - `@dataclass(frozen=True) class SyncRequest: application_id: int | None; create_issues: bool; min_level: Severity | None`
  - `@dataclass(frozen=True) class SyncOutcome: application_id: int; created: int; closed: int; linked: int; reopened: int; message: str`
  - `class SyncGitHubIssues: __init__(self, uow: UnitOfWork, tracker: IssueTracker, formatter: IssueFormatter, drafts: ExportApplicationIssues, clock: Callable[[], datetime]) -> None` · `execute(self, request: SyncRequest) -> list[SyncOutcome]`
- Verhalten (Spec „Use Case“): je Anwendung mit Repo, Fehler je Anwendung abfangen (`IssueTrackerError` und andere Fehler → `github_sync_message`), ein Commit je Anwendung. Schritt 1 Abgleich (über `decide_issue_action`), Schritt 2 Anlegen (Schwelle, Duplikat per Marker, bei Automatik `first_seen_at ≥ auto_issue_enabled_at`), Schritt 3 Meldung speichern.
- Review Focus 2: `tracker.get` liefert `None` → Verknüpfung bleibt, Meldung „Issue #n nicht gefunden“, keine Statusänderung.

- [ ] **Step 1: Failing tests** – Anlegen: nur ≥ Schwelle, Reihenfolge nach Risiko, Duplikat per Marker verknüpft statt angelegt, bestehende `issue_url` übersprungen; Automatik legt nur Treffer mit neuem `first_seen_at` an; Abgleich-Szenario „open → closed completed“ setzt aktive offene Treffer auf `behoben` mit Auflösung; Fehler in Anwendung A (Tracker wirft) → Anwendung B läuft; `get` → `None` (Review Focus 2); Meldungstext „3 angelegt, 1 geschlossen, 2 verknüpft“.
- [ ] **Step 2: Run** `uv run pytest tests/unit/test_github_sync.py -v` → FAIL.
- [ ] **Step 3: Implementieren** – Methoden aufteilen: `_sync_existing_links`, `_create_missing`, `_sync_one(application)`; je ≤ Komplexität 8.
- [ ] **Step 4: Run** → PASS; `make check`.
- [ ] **Step 5: Commit** `feat: sync GitHub issue status and create issues per application`

### Task 5: Adapter `GitHubAppIssueTracker`

**Files:**
- Create: `backend/app/infrastructure/github/__init__.py`, `backend/app/infrastructure/github/app_client.py`, `backend/app/infrastructure/github/jwt_signer.py` (kleine Funktionen: JWT, Installations-Token-Cache)
- Create: `backend/app/presentation/issue_formatter.py` (`IssueFormatter`-Implementierung, nutzt bestehende Titel-/Label-/Body-Funktionen aus `presentation/issue_export_markdown.py`)
- Modify: `backend/pyproject.toml` (`PyJWT[crypto]`, per `uv add "PyJWT[crypto]"`, Dependency-Freigabe liegt vor)
- Modify: `backend/app/infrastructure/config.py` (`github_app_id: str | None`, `github_app_private_key_file: Path = Path("/run/secrets/github_app_private_key")`, `github_api_url: str = "https://api.github.com"`)
- Test: `backend/tests/unit/test_github_app_client.py` (`httpx.MockTransport`, Testschlüssel per Fixture erzeugt)

**Interfaces:**
- Consumes: Task 1 Port.
- Produces: `GitHubAppIssueTracker(settings: Settings, transport: httpx.BaseTransport | None = None, clock: Callable[[], datetime])` implementiert `IssueTracker`.

- [ ] **Step 1: Failing tests** – JWT: RS256, `iss` = App-ID, `iat` = now − 60, `exp` = now + 9 min (mit Testschlüssel verifizieren); Installations-Token wird gecacht und vor Ablauf (5 min) erneuert; `existing_markers` folgt Link-Header über zwei Seiten, ignoriert Pull Requests; `create` legt fehlende Labels an (422 „already exists“ ignoriert); `set_open` postet Kommentar vor `PATCH` mit `state_reason: completed` bzw. `not_planned`; `get` bei 404 → `None`; 401/403 → `IssueTrackerError` ohne Token im Text; 429 bzw. 403 mit `x-ratelimit-remaining: 0` → „Rate-Limit erreicht“; `is_configured()` False bei leerer Key-Datei oder fehlender App-ID; zwischen zwei `create` wird 1 s gewartet (Sleep injizierbar).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implementieren**; Marker-Regex und Pagination in eigene kleine Funktionen; Schlüssel nur in `_load_private_key()` gelesen.
- [ ] **Step 4: Run** → PASS; `make check`; Architektur-Review (Adapter nur in `infrastructure`, Formatter in `presentation`, Verdrahtung in `main.py`).
- [ ] **Step 5: Commit** `feat: add GitHub App adapter for issue tracking`

### Task 6: Runner, Verdrahtung, API

**Files:**
- Modify: `backend/app/infrastructure/thread_ingest_runner.py` → generalisieren zu `ThreadJobRunner` (gemeinsame Sperre; Jobs nacheinander, nie gleichzeitig); Datei ggf. umbenennen, Importe anpassen
- Modify: `backend/app/application/ingest.py` (`run_ingest_job` ruft nach dem Commit `SyncGitHubIssues(SyncRequest(None, False, None))` in eigener UoW auf, nur wenn Tracker konfiguriert; Ausnahme geloggt)
- Modify: `backend/app/main.py` (Verdrahtung Tracker, Formatter, Runner)
- Modify: `backend/app/presentation/inventory_router.py` (`PATCH /applications/{id}` mit `githubRepository`, `autoIssueMinLevel`; Detailfelder `githubRepository`, `autoIssueMinLevel`, `githubSyncedAt`, `githubSyncMessage`)
- Create: `backend/app/presentation/github_router.py` (`POST /applications/{id}/github/sync` → 202/409/503; `GET /github/status` → `{configured, running}`)
- Modify: `backend/app/presentation/schemas.py` (Pydantic-DTOs, `ApiModel`, camelCase; Repo-Regex `^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$` als Pattern)
- Modify: `scripts/generate-secrets.sh` (`secrets/github_app_private_key.pem` leer anlegen, falls fehlend), `compose.yaml` / `compose.dev.yaml` (Secret nur am Backend)
- Test: `backend/tests/unit/test_thread_ingest_runner.py` (erweitern), `backend/tests/api/test_github_api.py`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: `POST /api/applications/{id}/github/sync`, Body `{"createIssues": bool, "minLevel": "niedrig"|"mittel"|"hoch"|"kritisch"|null}`; `GET /api/github/status`.

- [ ] **Step 1: Failing tests** – Runner: zweiter Start während Scan → `False`; Sync-Start während Scan → 409; Scan-Start während Sync → 409; PATCH mit Repo `"a/b\nc"` oder `"../x"` → 422; PATCH ohne GitHub-Konfiguration erlaubt (Repo speicherbar), Sync → 503; Detail liefert neue Felder; Scan-Ergebnis bleibt erhalten, wenn Sync wirft.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implementieren**, Router ohne Logik (Use Case aufrufen).
- [ ] **Step 4: Run** → PASS; `make check`.
- [ ] **Step 5: Commit** `feat: wire GitHub sync into scan runner and API`

### Task 7: Oberfläche (Feature `inventory`)

**Files:**
- Create: `frontend/src/features/inventory/model/github.ts` (zod-Schemas, Typen; Severity-Auswahl)
- Create: `frontend/src/features/inventory/api/github-api.ts`, `frontend/src/features/inventory/hooks/use-github.ts` (TanStack Query: Status, Sync-Start, PATCH)
- Create: `frontend/src/features/inventory/components/application-github-dialog.tsx` (RHF + zod, Felder Repository und „Neue CVEs automatisch anlegen ab“)
- Create: `frontend/src/features/inventory/components/github-sync-controls.tsx` (Buttons „Issues in GitHub anlegen“ mit Mindest-Risiko-Dialog, „Mit GitHub abgleichen“, Statuszeile)
- Modify: CVE-Reiter-Komponente in `features/inventory/components/` (neben „Für KI exportieren“), Detail-Kopf (GitHub-Button), Tabelle (Spalte „Issue“ mit `rel="noopener"`, `target="_blank"`)
- Test: Vitest-Tests neben den Komponenten (`getByTestId`)

**Interfaces:**
- Consumes: Task 6 API.
- Produces: keine Backend-Schnittstelle.

Test-IDs (Schema `<feature>-<element>-<zweck>`): `inventory-btn-github-sync`, `inventory-btn-github-create`, `inventory-btn-github-settings`, `inventory-dialog-github-settings`, `inventory-dialog-github-create`, `inventory-select-github-min-level`, `inventory-input-github-repository`, `inventory-text-github-sync-status`, `inventory-link-github-issue-${cveId}`, `inventory-error-github-repository`.

- [ ] **Step 1: Failing Vitest-Tests** – Buttons deaktiviert ohne Repo / ohne Konfiguration / während Lauf (mit Hinweistext); Repository-Validierung zeigt `FieldError`; Issue-Link öffnet in neuem Tab mit `rel="noopener"`; Statuszeile zeigt Zeit und Meldung.
- [ ] **Step 2: Run** `cd frontend && npx vitest run` → FAIL.
- [ ] **Step 3: Implementieren** – shadcn-Komponenten zuerst per `npx shadcn@latest search` / MCP prüfen; nur semantische Farben; Icons lucide-react.
- [ ] **Step 4: Run** `npx vitest run`, `npx eslint .`, `npx tsc -b`, `make check` → grün.
- [ ] **Step 5: Commit** `feat: add GitHub settings and sync controls to the inventory view`

### Task 8: Abschluss und Praxisdurchlauf

**Files:** keine Codeänderungen erwartet; ggf. `docs/` (Betriebshinweis zur GitHub App in `docs/local-development.md`).

- [ ] **Step 1: `make check`** vollständig grün; Architektur-Review über alle Änderungen.
- [ ] **Step 2: Betriebshinweis** ergänzen: App anlegen (Rechte *Issues: Read & write*, *Metadata: Read*, kein Webhook), App-ID in ENV, Schlüssel nach `secrets/github_app_private_key.pem`.
- [ ] **Step 3: Echter Durchlauf** gegen ein Test-Repo des Nutzers (sobald die App angelegt ist): Anlegen per Button, manuell schließen → Abgleich, wieder öffnen → Treffer wird wieder „offen“. Ergebnis im Abschlussbericht festhalten; ohne App nur bis zu Schritt 2.
- [ ] **Step 4: Commit** `docs: describe GitHub App setup`

---

## Offene Punkte aus dem Spec (vor Task 5 klären)
- Keine. Die Festlegungen des Designers (Abschnitt „Festlegungen des Designers nach Builder-Check“) sind übernommen.
