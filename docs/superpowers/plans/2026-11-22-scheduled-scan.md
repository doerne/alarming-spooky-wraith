# Täglicher Scan nach Zeitplan – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Der Scan läuft täglich automatisch (APScheduler), verpasste Läufe werden nachgeholt, jedes Lauf-Ergebnis wird gespeichert, und das UI zeigt global und je Anwendung „Stand von …“ mit Warnungen.

**Architecture:** Neue Domain `ScanRun` + Repository-Port; Use Cases zeichnen jeden Lauf auf (um den bestehenden Scan-Job gewickelt), entscheiden über das Nachholen und liefern den Verlauf. APScheduler steckt nur in einem Infrastructure-Adapter, `main.py` verdrahtet ihn im Lifespan. Das Frontend bekommt Schema, reine Berechnung und Anzeige in `shared/`, beide Features nutzen sie.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2, Alembic, APScheduler 3.11 · React, TypeScript, TanStack Query, zod, Vitest

**Spec:** `docs/superpowers/specs/2026-11-22-scheduled-scan-design.md`

## Global Constraints

- Neue Abhängigkeit nur `apscheduler>=3.11,<4` (freigegeben). Keine weitere (auch nicht `tzdata`) ohne Rückfrage.
- ENV: `SCAN_SCHEDULE_ENABLED` (Standard `true`), `SCAN_SCHEDULE_TIME` (Standard `"04:00"`, Format `HH:MM`), `SCAN_SCHEDULE_TIMEZONE` (Standard `"Europe/Berlin"`).
- Abgeschaltet → kein Cron-Job **und** kein Nachholen.
- Nachholen nur, wenn der letzte regulär beendete Lauf (nicht `interrupted`) vor > 24 h begann oder fehlt **und** in den letzten 24 h kein `catch_up`-Lauf startete.
- `outcome`: `ok` (keine Quelle `unreliable`), `incomplete` (mind. eine), `failed` (Ausnahme). GitHub-Abgleich fließt nicht ein.
- Abgebrochener Lauf: `outcome=failed`, `interrupted=true`, `finished_at` = Reset-Zeit, `message="durch Neustart abgebrochen"`.
- UI-Warnschwelle „älter als ein Tag“: `lastUsableRun.finishedAt` > **26 h** alt.
- Texte exakt: „Scan läuft seit HH:MM“, „Noch kein vollständiger Scan“, „Stand: heute HH:MM“ / „Stand: DD.MM. HH:MM“, Zusätze „älter als ein Tag“, „n Quellen mit Fehlern“ (1 → „1 Quelle mit Fehlern“), „letzter Scan fehlgeschlagen“, Trenner „ · “; je Anwendung „Noch nicht gescannt – Änderungen seit dem letzten Scan“.
- Clean Architecture, Test-IDs `<feature>-<element>-<zweck>`, nur semantische Farben, Kommentare deutsch – siehe `CLAUDE.md`. Nach jedem Task `make check` grün.

## Review Focus

1. Ungültige `SCAN_SCHEDULE_TIME` (`"4:00"`, `"24:00"`, `"abc"`) oder Zeitzone (`"Mars/Base"`) → Backend startet nicht, Meldung nennt Variable und Wert. → Task 3, Step 1.
2. Der Scheduler-Job wirft (z. B. Runner-Ausnahme) → wird geloggt, Scheduler läuft weiter, nächster Tag startet normal. → Task 3, Step 1.
3. MariaDB liefert Zeitstempel ohne Zeitzone → Repository gibt UTC-aware `datetime` zurück; Vergleiche im Nachholen werfen nicht. → Task 1, Step 1.
4. Abgelehnter SBOM-Upload (gleiche Datei erneut) markiert die Anwendung **nicht** als geändert. → Task 4, Step 1.
5. Scan-Job wirft vor dem ersten Quellenzugriff (DB weg) → Lauf landet als `failed` mit Meldung „Lauf fehlgeschlagen (<Typ>)“, keine offene Zeile bleibt zurück. → Task 2, Step 1.

---

### Task 1: Scan-Läufe im Domain-Modell und in der Datenbank

**Files:**
- Create: `backend/app/domain/scan_run.py`
- Modify: `backend/app/domain/ports.py` (Port), `backend/app/application/unit_of_work.py` (Property `scan_runs`)
- Modify: `backend/app/infrastructure/models.py` (`ScanRunModel`), `backend/app/infrastructure/repositories.py` (`SqlScanRunRepository`), `backend/app/infrastructure/unit_of_work.py`
- Create: `backend/migrations/versions/<rev>_scan_run.py` (autogenerate, dann prüfen)
- Modify: `backend/tests/fakes.py` (`FakeScanRunRepository`, Property im Fake-UoW)
- Test: `backend/tests/unit/test_scan_run_domain.py`, `backend/tests/unit/test_repositories.py`

**Interfaces:**
- Produces (`app/domain/scan_run.py`):
  - `class ScanTrigger(StrEnum): MANUAL="manual"; SCHEDULE="schedule"; CATCH_UP="catch_up"`
  - `class ScanOutcome(StrEnum): OK="ok"; INCOMPLETE="incomplete"; FAILED="failed"`
  - `SCAN_MESSAGE_MAX_LENGTH = 500`, `INTERRUPTED_SCAN_MESSAGE = "durch Neustart abgebrochen"`
  - `@dataclass(frozen=True) class ScanRun`: `trigger: ScanTrigger`, `started_at: datetime`, `id: int | None = None`, `finished_at: datetime | None = None`, `outcome: ScanOutcome | None = None`, `components_scanned: int | None = None`, `findings_found: int | None = None`, `sources_with_errors: int = 0`, `message: str = ""`, `interrupted: bool = False`
  - `ScanRun.finish(self, outcome: ScanOutcome, finished_at: datetime, *, components_scanned: int | None = None, findings_found: int | None = None, sources_with_errors: int = 0, message: str = "") -> ScanRun` (kürzt `message` auf 500)
  - `ScanRun.interrupt(self, now: datetime) -> ScanRun`
  - Property `ScanRun.usable -> bool` (beendet und `outcome` in OK/INCOMPLETE)
- Produces (`ports.py`): `class ScanRunRepository(Protocol)`: `add(run) -> ScanRun`, `update(run) -> ScanRun`, `list_unfinished() -> list[ScanRun]`, `latest_finished() -> ScanRun | None`, `latest_usable() -> ScanRun | None`, `latest_regular_finished() -> ScanRun | None` (beendet, nicht `interrupted`), `latest_started(trigger: ScanTrigger) -> ScanRun | None`. „latest“ = höchstes `started_at`.
- Produces: `UnitOfWork.scan_runs: ScanRunRepository`

- [ ] **Step 1: Failing tests**
  - Domain: `finish(ScanOutcome.OK, t)` setzt `finished_at`, `usable is True`; `INCOMPLETE` → `usable`; `FAILED` → nicht `usable`; unbeendet → nicht `usable`; `message` mit 600 Zeichen → 500; `interrupt(t)` → `outcome FAILED`, `interrupted True`, `message == INTERRUPTED_SCAN_MESSAGE`, `finished_at == t`.
  - Repository (bestehendes SQLite/Session-Muster in `test_repositories.py`): `add`/`update` Round-Trip; `latest_usable` überspringt neueren `failed`; `latest_regular_finished` überspringt `interrupted`; `latest_started(CATCH_UP)` filtert nach Trigger; `list_unfinished` nur ohne `finished_at`; **Review Focus 3:** gelesene `started_at` ist `tzinfo == UTC`.
  - Fake-Repository verhält sich gleich (in `test_fakes.py` die Grundfälle).
- [ ] **Step 2: Run** `cd backend && uv run pytest tests/unit/test_scan_run_domain.py tests/unit/test_repositories.py -q` → FAIL (Import fehlt)
- [ ] **Step 3: Implementieren** – Domain, Port, Model `scan_run` (Spalten wie Domain; `trigger`/`outcome` als `String(20)`, `message` `String(500)`, `interrupted` mit `server_default=false()`), Repository analog zu den bestehenden (UTC-Normalisierung wie dort), Fake, UoW-Property. Migration: `uv run alembic revision --autogenerate -m "scan run"`, Inhalt prüfen.
- [ ] **Step 4: Run** `uv run pytest -q` und `make check` → grün
- [ ] **Step 5: Commit** `feat: persist scan runs`

### Task 2: Jeden Lauf aufzeichnen und den Stand über die API liefern

**Files:**
- Create: `backend/app/application/scan_runs.py`
- Modify: `backend/app/application/ingest_runner.py` (`start(trigger)`), `backend/app/infrastructure/thread_ingest_runner.py` (Job bekommt Trigger), `backend/app/presentation/ingest_router.py`, `backend/app/main.py`
- Modify: `backend/app/application/source_use_cases.py` (`reset_interrupted_runs` setzt auch Scan-Läufe zurück)
- Test: `backend/tests/unit/test_scan_runs.py`, `backend/tests/unit/test_thread_ingest_runner.py`, `backend/tests/api/test_cve_radar_api.py` (oder neue `test_ingest_api.py`)

**Interfaces:**
- Consumes: Task 1 (`ScanRun`, `ScanTrigger`, `ScanOutcome`, `UnitOfWork.scan_runs`); `IngestResult`, `SourceRunResult.unreliable` aus `app/application/ingest.py`.
- Produces (`app/application/scan_runs.py`):
  - `outcome_of(result: IngestResult) -> tuple[ScanOutcome, int, str]` – (Outcome, Anzahl unreliable Quellen, Meldung `"<n> Quellen mit Fehlern: <key>, <key>"` bzw. `""`)
  - `run_recorded_scan(uow_factory: UnitOfWorkFactory, clock: Clock, scan: Callable[[], IngestResult], trigger: ScanTrigger) -> IngestResult` – legt Lauf an (eigene UoW, commit), führt `scan()` aus, beendet den Lauf (eigene UoW, commit); bei Ausnahme: `FAILED`, Meldung `f"Lauf fehlgeschlagen ({type(error).__name__})"`, Ausnahme erneut werfen.
  - `class ResetInterruptedScans(uow, clock)` – `execute() -> int`
  - `@dataclass(frozen=True) class ScanHistory: last_run: ScanRun | None; last_usable_run: ScanRun | None` und `class GetScanHistory(uow)` – `execute() -> ScanHistory`
- Produces: `IngestRunner.start(self, trigger: ScanTrigger = ScanTrigger.MANUAL) -> bool`; `ThreadIngestRunner(job: Callable[[ScanTrigger], IngestResult], clock, gate)`.
- Produces (API): `GET /api/ingest/status` und `POST /api/ingest/run` liefern zusätzlich `lastRun` und `lastUsableRun` (je `null` oder `{trigger, outcome, startedAt, finishedAt, componentsScanned, findingsFound, sourcesWithErrors, message}`).

- [ ] **Step 1: Failing tests**
  - `outcome_of`: alle Quellen OK → `(OK, 0, "")`; eine `ERROR` + eine `complete=False` → `(INCOMPLETE, 2, "2 Quellen mit Fehlern: nvd, snyk")`; nur `SKIPPED` → `OK`.
  - `run_recorded_scan` mit Fake-UoW: Erfolg → ein Lauf, beendet, Trigger übernommen, Zahlen aus dem Ergebnis; **Review Focus 5:** `scan` wirft `RuntimeError` → Lauf `FAILED`, Meldung „Lauf fehlgeschlagen (RuntimeError)“, `list_unfinished() == []`, Ausnahme kommt durch.
  - `ResetInterruptedScans`: unbeendeter Lauf → `interrupted`, Rückgabe 1; beendete bleiben unverändert.
  - `GetScanHistory`: neuerer `failed` + älterer `ok` → `last_run` ist der `failed`, `last_usable_run` der `ok`.
  - Runner: `start(ScanTrigger.SCHEDULE)` reicht den Trigger an den Job.
  - API: nach einem Lauf in der DB und **neuem** Runner (Zustand im Speicher leer) liefert `GET /api/ingest/status` `lastRun.outcome == "ok"` und `lastUsableRun` gesetzt; ohne Läufe beide `null`.
- [ ] **Step 2: Run** `uv run pytest tests/unit/test_scan_runs.py tests/unit/test_thread_ingest_runner.py tests/api -q` → FAIL
- [ ] **Step 3: Implementieren** – Use Cases wie oben; Router holt `GetScanHistory` über `UnitOfWorkDep`; `main.py`: `job = partial(run_recorded_scan, uow_factory, _now, partial(run_scan_then_sync, scan, automatic_sync))`; `reset_interrupted_runs` ruft zusätzlich `ResetInterruptedScans` (mit Uhr – Signatur `reset_interrupted_runs(uow_factory, clock)`, Aufrufer anpassen).
- [ ] **Step 4: Run** `uv run pytest -q`, `make check` → grün
- [ ] **Step 5: Commit** `feat: record every scan run and expose the last result`

### Task 3: Täglicher Zeitplan und Nachholen beim Start

**Files:**
- Modify: `backend/pyproject.toml`, `backend/uv.lock` (`uv add "apscheduler>=3.11,<4"`)
- Modify: `backend/app/infrastructure/config.py` (drei Settings)
- Create: `backend/app/application/scan_schedule.py`
- Create: `backend/app/infrastructure/scan_scheduler.py`
- Modify: `backend/app/presentation/app_factory.py` (`AppServices.on_shutdown`, Lifespan), `backend/app/main.py`
- Modify: `compose.yaml` (ENV `SCAN_SCHEDULE_TIME`, `SCAN_SCHEDULE_TIMEZONE`, `SCAN_SCHEDULE_ENABLED` mit `${…:-Standard}`)
- Test: `backend/tests/unit/test_scan_schedule.py`, `backend/tests/unit/test_scan_scheduler.py`, `backend/tests/api/test_app.py`

**Interfaces:**
- Consumes: Task 2 (`IngestRunner.start(trigger)`), Task 1 (`scan_runs.latest_regular_finished`, `latest_started`).
- Produces (`app/application/scan_schedule.py`):
  - `@dataclass(frozen=True) class ScanSchedule: hour: int; minute: int; timezone: str`
  - `parse_scan_schedule(time_text: str, timezone: str) -> ScanSchedule` – Muster `^([01]\d|2[0-3]):[0-5]\d$`, Zeitzone über `zoneinfo.ZoneInfo`; Fehler → `ValueError` mit Text, der `SCAN_SCHEDULE_TIME` bzw. `SCAN_SCHEDULE_TIMEZONE` und den Wert nennt.
  - `CATCH_UP_AFTER = timedelta(hours=24)`; `class DecideCatchUp(uow, clock)` – `execute() -> bool`
  - `start_catch_up_if_due(uow_factory: UnitOfWorkFactory, clock: Clock, runner: IngestRunner) -> bool`
- Produces (`app/infrastructure/scan_scheduler.py`): `class ApsScanScheduler(runner: IngestRunner, schedule: ScanSchedule)` mit `start(*, paused: bool = False) -> None`, `shutdown() -> None`, `job_trigger_description() -> str` (für Tests: `str(job.trigger)`); Job-ID `"daily-scan"`, `max_instances=1`, `coalesce=True`, `misfire_grace_time=3600`. Der Job ruft `runner.start(ScanTrigger.SCHEDULE)`, loggt bei `False` „Geplanter Scan übersprungen: es läuft bereits ein Lauf“ und fängt/loggt jede Ausnahme.
- Produces: `AppServices.on_shutdown: Callable[[], None] | None = None` (im Lifespan nach `yield`).

- [ ] **Step 1: Failing tests**
  - `parse_scan_schedule("04:00", "Europe/Berlin") == ScanSchedule(4, 0, "Europe/Berlin")`; **Review Focus 1:** `"4:00"`, `"24:00"`, `"abc"` → `ValueError` mit `"SCAN_SCHEDULE_TIME"` und dem Wert im Text; `"Mars/Base"` → `ValueError` mit `"SCAN_SCHEDULE_TIMEZONE"`.
  - `DecideCatchUp` (Fake-UoW, feste Uhr `now`): keine Läufe → `True`; letzter regulärer begann vor 23 h → `False`; vor 25 h → `True`; letzter regulärer `failed` vor 2 h → `False`; jüngster Lauf `interrupted` vor 1 h, regulärer vor 25 h → `True`; zusätzlich `catch_up` vor 3 h gestartet → `False`.
  - `start_catch_up_if_due`: fällig → `runner.start(ScanTrigger.CATCH_UP)` genau einmal; nicht fällig → nie.
  - `ApsScanScheduler` mit Fake-Runner, `start(paused=True)`: genau ein Job `"daily-scan"`, Trigger-Beschreibung enthält `hour='4'`, `minute='0'` und `Europe/Berlin`; `shutdown()` ohne Fehler. **Review Focus 2:** Job-Funktion direkt aufgerufen, Runner wirft → keine Ausnahme nach außen, Log-Eintrag (`caplog`); Runner gibt `False` → Log „übersprungen“.
  - App: `create_app(..., services=AppServices(on_shutdown=callback))` im `TestClient`-Kontext → `callback` nach Verlassen aufgerufen.
- [ ] **Step 2: Run** `uv run pytest tests/unit/test_scan_schedule.py tests/unit/test_scan_scheduler.py tests/api/test_app.py -q` → FAIL
- [ ] **Step 3: Implementieren** – Abhängigkeit per `uv add`; Settings `scan_schedule_enabled: bool = True`, `scan_schedule_time: str = "04:00"`, `scan_schedule_timezone: str = "Europe/Berlin"`; `main.py`: Schedule beim Bauen der App parsen (Fehler bricht Start ab); `on_startup` = Reset → (wenn aktiv) Nachholen → Scheduler-Start; `on_shutdown` = `scheduler.shutdown()`; abgeschaltet → weder Scheduler noch Nachholen.
- [ ] **Step 4: Prüfen, ob das Runtime-Image Zeitzonendaten hat:** `docker compose build backend && docker compose run --rm --no-deps backend python -c "import zoneinfo; print(zoneinfo.ZoneInfo('Europe/Berlin'))"` → gibt `Europe/Berlin` aus. Schlägt das fehl: anhalten und `tzdata` beim Nutzer anfragen.
- [ ] **Step 5: Run** `uv run pytest -q`, `make check` → grün
- [ ] **Step 6: Commit** `feat: run the scan daily and catch up missed runs at startup`

### Task 4: Inventar-Änderungen je Anwendung merken

**Files:**
- Modify: `backend/app/domain/inventory.py` (`Application.inventory_changed_at`, `mark_inventory_changed`)
- Modify: `backend/app/infrastructure/models.py`, `backend/app/infrastructure/repositories.py`; Migration `<rev>_inventory_changed_at.py`
- Modify: `backend/app/application/inventory_use_cases.py` (`CreateApplication`, `AddComponent`, `UpdateComponent` bekommen `clock`), `backend/app/application/sbom_use_cases.py` (`UploadSbomVersion`, `DeleteSbom`)
- Modify: `backend/app/presentation/inventory_router.py`, `backend/app/presentation/sbom_router.py` (Uhr durchreichen, `inventoryChangedAt` in `ApplicationDetailResponse`)
- Test: `backend/tests/unit/test_inventory_use_cases.py`, `backend/tests/unit/test_sbom_use_cases.py`, `backend/tests/api/test_cve_radar_api.py`

**Interfaces:**
- Produces: `Application.inventory_changed_at: datetime | None = None`; `Application.mark_inventory_changed(self, now: datetime) -> Application` (gibt Kopie zurück); API-Feld `inventoryChangedAt: string | null` in `GET /api/applications/{id}`.

- [ ] **Step 1: Failing tests**
  - `CreateApplication(uow, clock)` → `inventory_changed_at == now`; `AddComponent`, `UpdateComponent` → Anwendung hat `now`; `UploadSbomVersion` erfolgreich → `now`; `DeleteSbom(uow, clock)` → `now`.
  - **Review Focus 4:** gleiche SBOM-Datei zweimal → zweiter Upload wird abgelehnt (bestehender Fehler), `inventory_changed_at` bleibt beim Wert des ersten Uploads.
  - API: `GET /api/applications/{id}` enthält `inventoryChangedAt`.
- [ ] **Step 2: Run** `uv run pytest tests/unit/test_inventory_use_cases.py tests/unit/test_sbom_use_cases.py tests/api -q` → FAIL
- [ ] **Step 3: Implementieren** – Spalte `DateTime(timezone=True)`, nullable, Bestand bleibt NULL; Use Cases setzen den Wert vor ihrem `commit()` über `applications.update`.
- [ ] **Step 4: Run** `uv run pytest -q`, `make check` → grün
- [ ] **Step 5: Commit** `feat: remember when an application's inventory changed`

### Task 5: Anzeige „Stand von …“ auf der Schwachstellen-Seite

**Files:**
- Create: `frontend/src/shared/api/scan-status.ts`, `frontend/src/shared/lib/scan-freshness.ts` (+ `.test.ts`), `frontend/src/shared/components/scan-freshness.tsx` (+ `.test.tsx`)
- Modify: `frontend/src/features/cves/model/types.ts` (`ingestStateSchema` entfällt, nutzt Shared-Schema), `frontend/src/features/cves/api/cves-api.ts`, `frontend/src/features/cves/hooks/use-run-ingest.ts`, `frontend/src/features/cves/components/ingest-control.tsx` (+ Test), Container der Schwachstellen-Seite

**Interfaces:**
- Consumes: API aus Task 2.
- Produces (`shared/api/scan-status.ts`): `scanRunSchema`, `scanStatusSchema` (bisherige Felder + `lastRun`, `lastUsableRun` nullable), `type ScanStatus`, `type ScanRun`, `SCAN_STATUS_QUERY_KEY = ["ingest-status"] as const`, `fetchScanStatus(): Promise<ScanStatus>`.
- Produces (`shared/lib/scan-freshness.ts`): `STALE_AFTER_MS = 26 * 60 * 60 * 1000`; `interface ScanFreshnessInput { status: ScanStatus; now: Date; inventoryChangedAt?: string | null }`; `describeScanFreshness(input: ScanFreshnessInput): { text: string; warning: boolean }`.
- Produces (`shared/components/scan-freshness.tsx`): `ScanFreshness({ text, warning, testId }: { text: string; warning: boolean; testId: string })` – neutral `text-muted-foreground`; Warnung mit `TriangleAlert` (`aria-hidden`) und `text-destructive`.

- [ ] **Step 1: Failing tests** (`now = 2026-11-22T10:00` Ortszeit)
  - läuft, `startedAt` 04:00 → `{ text: "Scan läuft seit 04:00", warning: false }`
  - kein `lastUsableRun`, kein `lastRun` → `"Noch kein vollständiger Scan"`, `warning: false`; `lastRun` `failed` → gleicher Text, `warning: true`
  - `lastUsableRun` ok, beendet heute 04:12 → `"Stand: heute 04:12"`, `warning: false`
  - `incomplete` mit `sourcesWithErrors: 2` → `"Stand: heute 04:12 · 2 Quellen mit Fehlern"`, `warning: true`; mit 1 → „1 Quelle mit Fehlern“
  - beendet 2026-11-20 04:09 → `"Stand: 20.11. 04:09 · älter als ein Tag"`, `warning: true`; beendet vor 25 h → kein „älter“-Zusatz
  - `lastRun` `failed` neuer als `lastUsableRun` → Zusatz „letzter Scan fehlgeschlagen“
  - `inventoryChangedAt` nach `lastUsableRun.startedAt` → `"Noch nicht gescannt – Änderungen seit dem letzten Scan"`, `warning: true`; davor → normale Anzeige; läuft gerade → „Scan läuft …“ gewinnt
  - Komponente: rendert `getByTestId(testId)` mit Text; Warnung enthält ein `svg`.
  - `IngestControl`: zeigt `cves-text-scan-freshness`, „Letzter Scan: n Funde“ ist entfernt; Fehler-Alert `cves-error-ingest` bleibt.
- [ ] **Step 2: Run** `cd frontend && npx vitest run src/shared src/features/cves` → FAIL
- [ ] **Step 3: Implementieren** – Uhrzeiten mit `Intl.DateTimeFormat("de-DE", …)`; „heute“ = gleiches lokales Datum wie `now`. `IngestControl` bekommt `freshness: { text: string; warning: boolean }` als Prop; der Seiten-Container berechnet es mit `new Date()`.
- [ ] **Step 4: Run** `npx vitest run`, `npx eslint .`, `npx tsc -b`, `make check` → grün
- [ ] **Step 5: Commit** `feat: show scan freshness on the vulnerabilities page`

### Task 6: Stand im CVE-Reiter der Anwendung

**Files:**
- Create: `frontend/src/features/inventory/hooks/use-scan-status.ts`
- Modify: `frontend/src/features/inventory/model/types.ts` (Anwendungs-Schema `inventoryChangedAt: z.string().nullable()`), `frontend/src/features/inventory/application-detail-page.tsx`, `frontend/src/features/inventory/components/application-cves-panel.tsx` (+ `application-cves.test.tsx`)

**Interfaces:**
- Consumes: Task 5 (`fetchScanStatus`, `SCAN_STATUS_QUERY_KEY`, `describeScanFreshness`, `ScanFreshness`), Task 4 (`inventoryChangedAt`).
- Produces: `useScanStatus()` (TanStack Query, gleicher Key wie das cves-Feature, damit der Cache geteilt wird); `ApplicationCvesPanel` bekommt Prop `freshness: { text: string; warning: boolean } | undefined`.

- [ ] **Step 1: Failing tests** – Panel mit `freshness` zeigt `inventory-text-scan-freshness` mit dem Text, auch wenn keine Funde da sind (`inventory-text-no-cves` bleibt); ohne `freshness` nichts.
- [ ] **Step 2: Run** `npx vitest run src/features/inventory` → FAIL
- [ ] **Step 3: Implementieren** – Seite berechnet `describeScanFreshness({ status, now: new Date(), inventoryChangedAt })`.
- [ ] **Step 4: Run** `npx vitest run`, `npx eslint .`, `npx tsc -b`, `make check` → grün
- [ ] **Step 5: Commit** `feat: show scan freshness per application`

### Task 7: Doku, Gesamtprüfung, PR

**Files:**
- Modify: `README.md` (Abschnitt Datenquellen: täglicher Scan, Konfigurationstabelle um drei ENV-Werte), `docs/local-development.md` (Scan-Hinweis, Abschalten im Notweg mit `SCAN_SCHEDULE_ENABLED=false`)

- [ ] **Step 1:** Doku anpassen (Texte „einen Zeitplan gibt es noch nicht“ ersetzen).
- [ ] **Step 2:** `make check` grün; Subagent `architecture-reviewer` über den ganzen Branch, Befunde beheben.
- [ ] **Step 3:** Praxisprobe mit `make dev-services`: `SCAN_SCHEDULE_TIME` auf zwei Minuten in die Zukunft setzen, Backend neu starten → Log zeigt Nachholen bzw. geplanten Start; `GET /api/ingest/status` liefert `lastRun.trigger`.
- [ ] **Step 4: Commit** `docs: describe the daily scan`, Push, PR gegen `main`.
