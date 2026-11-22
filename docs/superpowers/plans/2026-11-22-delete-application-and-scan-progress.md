# Anwendung löschen und Scan-Fortschritt – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Anwendungen lassen sich samt Komponenten, SBOMs und Funden löschen. Während eines Scans zeigt die Schwachstellen-Seite, welche Quellen und Schlussschritte erledigt sind.

**Architecture:**
- **Löschen:** Use Case `DeleteApplication` über bestehende Repository-Ports plus `ApplicationRepository.delete`. Eine Sperre über den neuen Port `JobActivity`, implementiert von `JobGate`, verhindert Löschen während eines Scans oder Abgleichs. Endpoint `DELETE /api/applications/{id}`.
- **Fortschritt:** Port `ScanProgress` in `application`. Eine thread-sichere Implementierung in `infrastructure` hält die Schritte. `RunIngest` und `run_scan_then_sync` melden Zustände. Der Runner startet die Liste und gibt sie über `/api/ingest/status` als `steps` aus.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2 · React, TanStack Query, zod, shadcn/ui (`dialog`, `button`), lucide-react.

**Spec:** `docs/superpowers/specs/2026-11-22-delete-application-and-scan-progress-design.md`

## Global Constraints

- **Löschen** entfernt Funde → Komponenten → SBOM-Versionen und SBOMs → Anwendung in einer Transaktion. Advisories, Aliase, Quellen-Einstellungen und `scan_run` bleiben. GitHub wird nicht angefasst.
- **Sperre:** Läuft ein Scan oder Abgleich, antwortet `DELETE` mit 409. Meldung im UI: „Während eines Scans oder GitHub-Abgleichs kann nicht gelöscht werden.“
- **Dialog-Texte:**
  - Titel: „<Name> löschen?“
  - Beschreibung: „<Name> mit N Komponenten, M SBOMs und K Funden endgültig löschen?“ und „Bereits angelegte GitHub-Issues bleiben auf GitHub bestehen.“
  - Buttons: „Abbrechen“ und „Endgültig löschen“; Button im Kopf: „Anwendung löschen“.
- **Fortschrittsschritte:**
  - Reihenfolge: alle Quellen in Registry-Reihenfolge, dann `persist` („Funde speichern“), dann `github-sync` („GitHub-Abgleich“).
  - Zustände: `pending`, `running`, `done`, `skipped`, `failed`.
- **Anzeige:**
  - „Scan läuft · X von Y Quellen erledigt“; erledigt sind `done`, `skipped` und `failed` unter den Quellen.
  - Der Balken zeigt den Anteil erledigter Schritte an allen Schritten.
  - Die Anzeige erscheint nur bei `running` und auf der Schwachstellen-Seite.
- **Icons je Zustand:** `pending` Circle, `running` Loader2 (animate-spin), `done` Check, `skipped` Minus, `failed` X (`text-destructive`). Bei übersprungenen Quellen steht die Begründung im `title`.
- **Regeln:**
  - Keine neuen Abhängigkeiten. Keine Änderungen in `frontend/src/shared/ui/`. Nur semantische Farben.
  - Test-IDs `<feature>-<element>-<zweck>`, kebab-case.
  - Python: mypy strict, Komplexität ≤ 8, ≤ 5 Parameter. TS: strict, kein `any`, ≤ 4 Parameter.
  - Kommentare auf Deutsch, Bezeichner Englisch, UI-Texte Deutsch.
- **Ablauf:**
  - Nach jeder Task `make check` grün. Den Subagent `fullstack-standards:architecture-reviewer` startet der Controller.
  - Commit-Format `feat: …`, `fix: …`, `refactor: …` mit Trailern
    `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` und
    `Claude-Session: https://claude.ai/code/session_01HoSCtHbaSEToQC55z1Hq5A`.

## Review Focus

1. **Löschen gegen echte Fremdschlüssel:** `component.sbom_id` und `retired_in_version_id` zeigen auf SBOM und Version, `finding` auf Komponente und Anwendung. Die Reihenfolge muss in MariaDB ohne FK-Fehler durchlaufen (Task 1, Repository-Test).
2. **Andere Anwendungen bleiben unberührt:** Ihre Funde und SBOMs, auch gemeinsam genutzte Advisories, bleiben erhalten (Task 1).
3. **Scan, der mit Exception abbricht:** Laufende Schritte dürfen nicht ewig auf `running` stehen. Nach Ende des Laufs zeigt das UI ohnehin nichts mehr, der Status liefert `running=false` (Task 3).
4. **Quelle übersprungen, weil kein Key oder deaktiviert:** `skipped` mit Begründung, nicht `failed` (Task 3).
5. **GitHub nicht konfiguriert:** `github-sync` = `skipped`. Scheitert der Abgleich, ist er `failed`, und der Scan zählt trotzdem als erledigt (Task 3).

---

### Task 1: Backend – Anwendung löschen

**Files:**
- Modify: `backend/app/domain/ports.py` (`ApplicationRepository.delete`), `backend/app/domain/errors.py` (`ApplicationBusyError(ConflictError)`)
- Create: `backend/app/application/job_activity.py` (Port), `backend/app/infrastructure/job_gate.py` erfüllt den Port unverändert (`try_acquire`/`release`)
- Modify: `backend/app/application/inventory_use_cases.py` (`DeleteApplication`)
- Modify: `backend/app/infrastructure/repositories.py`, `backend/tests/fakes.py`
- Modify: `backend/app/presentation/inventory_router.py`, `backend/app/presentation/app_factory.py` (`AppServices.job_activity`), `backend/app/main.py` (vorhandene `gate` übergeben)
- Test: `backend/tests/unit/test_inventory_use_cases.py`, `backend/tests/unit/test_repositories.py`, `backend/tests/api/test_cve_radar_api.py` (oder neue `test_delete_application_api.py`)

**Interfaces:**
- Produces:
  - `class JobActivity(Protocol): def try_acquire(self) -> bool: ...; def release(self) -> None: ...`, erfüllt von `JobGate`. `IDLE_ACTIVITY` (immer frei) ist der Default, den `app_factory` setzt, wenn kein `job_activity` übergeben wird.
  - *(Umgesetzt nach Review, ersetzt die ursprüngliche Prüfung per `is_busy()`: Das Löschen hält die Sperre über Löschen und Commit, sonst könnte zwischen Prüfung und Commit ein Scan starten.)*
  - `ApplicationRepository.delete(application_id: int) -> None`
  - `class ApplicationBusyError(ConflictError)` mit deutscher Meldung „Während eines Scans oder GitHub-Abgleichs kann nicht gelöscht werden.“
  - `DeleteApplication(uow: UnitOfWork, activity: JobActivity).execute(application_id: int) -> None`:
    - prüft zuerst die Existenz (`applications.get`, sonst `EntityNotFoundError` → 404), dann `activity.try_acquire()`; schlägt das fehl → `ApplicationBusyError`. Löschen und Commit laufen in `try/finally` mit `release()`.
    - löscht danach über die vorhandenen Ports: `findings.delete_for_components(ids aller Komponenten der Anwendung)` (inkl. ausgebauter), `components.delete_many`, je SBOM `sboms.delete` (prüfen, ob das Versionen mitlöscht; sonst `sbom_versions` vorher), `applications.delete`, `commit()`.
  - `DELETE /api/applications/{application_id}` → 204. Die Router-Dependency liest nur `app.state.job_activity` (Default `IDLE_ACTIVITY` setzt `app_factory`).

- [ ] **Step 1: Failing tests**
  - Use Case (Fakes):
    - Zwei Anwendungen mit Komponente, Fund und SBOM; nach dem Löschen von A sind A, ihre Komponenten, Funde und SBOMs weg. B ist vollständig da, die Advisory existiert noch.
    - Unbekannte ID → `EntityNotFoundError`.
    - Sperre belegt → `ApplicationBusyError`, nichts gelöscht; nach Erfolg und nach Fehler ist die Sperre wieder frei.
  - Repository (`test_repositories.py`, SQLite/DB-Fixture wie dort üblich): Anwendung mit SBOM-Version, ausgebauter Komponente (`retired_in_version_id`) und Fund lässt sich ohne FK-Fehler löschen.
  - API: 204, dann `GET /api/applications/{id}` → 404; unbekannt → 404; busy-Fake → 409.
- [ ] **Step 2–4:** rot → umsetzen → grün, dann `make check`.
- [ ] **Step 5:** Commit `feat: delete applications with their components, SBOMs and findings`.

### Task 2: Frontend – Anwendung löschen

**Files:**
- Modify: `frontend/src/features/inventory/api/…` (Funktion `deleteApplication(id)`, Muster wie die bestehende SBOM-Löschung)
- Create: `frontend/src/features/inventory/hooks/use-delete-application.ts`
- Create: `frontend/src/features/inventory/components/delete-application-dialog.tsx` (+ `.test.tsx`), Muster `sbom-delete-dialog.tsx`
- Modify: `frontend/src/features/inventory/components/detail-header.tsx`, `frontend/src/features/inventory/application-detail-page.tsx` (+ Tests)

**Interfaces:**
- **Hook:** `useDeleteApplication(applicationId)` invalidiert bei Erfolg `["applications"]`, `queryKeys.application(id)`, `queryKeys.applicationFindings(id)` und `queryKeys.findings`. Danach ruft die Seite ihren bestehenden Zurück-Callback auf (`onBack`).
- **Dialog:** `DeleteApplicationDialog({ name, counts: { components, sboms, findings }, isDeleting, error, onConfirm, onCancel })`.
  - Texte wie in den Global Constraints.
  - Bei 409 erscheint der Text der Global Constraints in `inventory-error-delete-app`.
- **Zählwerte:** Die Seite ermittelt sie aus vorhandenen Abfragen: Komponenten aus der Anwendung, SBOMs aus der SBOM-Liste, Funde aus `unfilteredTotal` der Fundabfrage. Fehlt ein Wert, steht „0“.
- **Test-IDs:** `inventory-btn-delete-app`, `inventory-dialog-delete-app`, `inventory-btn-confirm-delete-app`, `inventory-btn-cancel-delete-app`, `inventory-error-delete-app`.

- [ ] **Step 1:** Tests:
  - Dialog: Text mit Zahlen und Name, Bestätigen ruft `onConfirm`, Fehlertext.
  - Seite: Klick → Dialog → Bestätigen → `DELETE /api/applications/<id>` und `onBack`; bei 409 bleibt der Dialog offen und zeigt die Meldung.
- [ ] **Step 2–4:** rot → umsetzen → grün, dann `make check`.
- [ ] **Step 5:** Commit `feat: delete an application from its detail view`.

### Task 3: Backend – Scan-Fortschritt

**Files:**
- Create: `backend/app/application/scan_progress.py`, `backend/app/infrastructure/scan_progress_tracker.py`
- Modify: `backend/app/application/ingest.py` (`RunIngest`, `run_ingest_job`, `run_scan_then_sync`), `backend/app/application/github_sync.py` (`run_github_sync` → `bool`), `backend/app/application/ingest_runner.py` (`IngestRunState.steps`), `backend/app/infrastructure/thread_ingest_runner.py`, `backend/app/presentation/ingest_router.py`, `backend/app/main.py`
- Test: `backend/tests/unit/test_ingest.py`, `backend/tests/unit/test_thread_ingest_runner.py`, `backend/tests/unit/test_scan_then_sync.py`, neue `backend/tests/unit/test_scan_progress_tracker.py`, API-Test für `/api/ingest/status`

**Interfaces:**
- **`application/scan_progress.py`:**
  - `class StepState(StrEnum)` mit `PENDING="pending"`, `RUNNING="running"`, `DONE="done"`, `SKIPPED="skipped"`, `FAILED="failed"`.
  - `@dataclass(frozen=True) class ScanStep: key: str; label: str; state: StepState = PENDING; detail: str = ""`
  - `PERSIST_STEP = "persist"`, `GITHUB_SYNC_STEP = "github-sync"`.
  - `class ScanProgress(Protocol)`: `def begin(self, steps: Sequence[ScanStep]) -> None` und `def update(self, key: str, state: StepState, detail: str = "") -> None`.
  - `NO_PROGRESS`: No-op-Implementierung als Default.
  - `def initial_steps(descriptors: Sequence[SourceDescriptor]) -> list[ScanStep]`: Quellen (`key`, `name`), dann „Funde speichern“, dann „GitHub-Abgleich“.
- **`infrastructure/scan_progress_tracker.py`:** `ScanProgressTracker` ist thread-sicher (Lock), erfüllt `ScanProgress` und hat zusätzlich `snapshot() -> tuple[ScanStep, ...]`. `update` bei unbekanntem Key ignoriert.
- **`RunIngest(..., progress: ScanProgress = NO_PROGRESS)`:**
  - Je Quelle vor dem Lauf `RUNNING`.
  - Danach `DONE` bei OK, `SKIPPED` mit Skip-Meldung als `detail`, `FAILED` mit Fehlermeldung.
  - Um `_persist`/Resolve herum `PERSIST_STEP` `RUNNING`, dann `DONE`.
- **`run_github_sync`** gibt `bool` zurück (False ohne Konfiguration).
- **`run_scan_then_sync(scan, sync: Callable[[], bool], progress=NO_PROGRESS)`:** `github-sync` `RUNNING`, danach `DONE`, `SKIPPED` (False) oder `FAILED` (Exception).
- **`ThreadIngestRunner(job, clock, gate, progress: ScanProgressTracker | None = None, steps: Callable[[], Sequence[ScanStep]] = list)`:** `start` ruft `progress.begin(steps())`. `state()` liefert `IngestRunState(..., steps=progress.snapshot())`.
- **`IngestRunState.steps: tuple[ScanStep, ...] = ()`**
- **Status-Endpoint:** `IngestStateResponse.steps: list[ScanStepResponse(key, label, state, detail)]` in camelCase.
- **`main.py`:** Ein Tracker wird an `run_ingest_job`/`RunIngest`, `run_scan_then_sync` und den Runner gegeben, dazu `steps=lambda: initial_steps(registry.descriptors())`.

- [ ] **Step 1: Failing tests**
  - `RunIngest` mit Fake-Progress (Liste der Aufrufe): eine OK-Quelle, eine übersprungene und eine fehlerhafte (Muster aus `test_ingest.py`). Erwartete Aufrufe der Reihe nach: `(ok, RUNNING)`, `(ok, DONE)`, `(skip, SKIPPED, "<Meldung>")`, `(err, RUNNING)`, `(err, FAILED, …)`, `(persist, RUNNING)`, `(persist, DONE)`.
  - `run_scan_then_sync`:
    - `sync` liefert True → `github-sync` DONE.
    - `sync` liefert False → SKIPPED.
    - `sync` wirft → FAILED, und das Ergebnis des Scans wird trotzdem zurückgegeben.
  - Tracker:
    - `begin` setzt alle auf PENDING.
    - `update` ändert genau einen Schritt.
    - Unbekannter Key wird ignoriert.
    - `snapshot` ist eine Kopie.
  - Runner: Nach `start` liefert `state().steps` die initialen Schritte, alle PENDING.
  - API: `GET /api/ingest/status` enthält `steps` mit Schlüsseln `key`, `label`, `state`, `detail`.
- [ ] **Step 2–4:** rot → umsetzen → grün, dann `make check`.
- [ ] **Step 5:** Commit `feat: report scan progress per source`.

### Task 4: Frontend – Fortschrittsanzeige

**Files:**
- Modify: `frontend/src/shared/api/scan-status.ts` (Schema `steps`, Default `[]` für ältere Antworten nicht nötig, das Backend liefert immer)
- Create: `frontend/src/features/cves/components/scan-progress.tsx` (+ `.test.tsx`)
- Modify: `frontend/src/features/cves/components/ingest-control.tsx` (+ Test), Fixtures, die `scanStatusSchema` nutzen

**Interfaces:**
- **`ScanProgress({ steps })`:** rein, gerendert von `IngestControl` nur bei `state.running && state.steps.length > 0`, unter dem Button über die ganze Breite.
- **Texte und Icons:** wie in den Global Constraints.
- **Balken:** `div` mit `role="progressbar"`, `aria-valuemin=0`, `aria-valuemax=100`, `aria-valuenow` (gerundet) und `aria-label="Scan-Fortschritt"`; Füllung `bg-primary` auf `bg-muted`.
- **Schritte:** als umbrechende Chips (`flex flex-wrap gap-2 text-xs`).
- **Test-IDs:** `cves-card-scan-progress`, `cves-text-scan-progress`, `cves-item-scan-step-<key>` (Key bleibt, z. B. `cves-item-scan-step-github-sync`).

- [ ] **Step 1:** Tests:
  - 21 Quellen-Schritte (7 done, 1 skipped, 1 running, Rest pending) plus 2 Schlussschritte → Text „Scan läuft · 8 von 21 Quellen erledigt“.
  - `aria-valuenow` = round(8/23·100) = 35.
  - Fehlgeschlagener Schritt hat `text-destructive`.
  - `IngestControl` zeigt die Anzeige nur bei `running`.
- [ ] **Step 2–4:** rot → umsetzen → grün, dann `make check`.
- [ ] **Step 5:** Commit `feat: show scan progress next to the scan button`.

### Task 5: Abschluss

- [ ] **Step 1:** README ergänzen: im Inventar einen Hinweis zu „Anwendung löschen“, bei den Datenquellen einen Hinweis zum Fortschritt.
- [ ] **Step 2:** `make check` grün.
- [ ] **Step 3:** `make dev-services`, dann im Browser prüfen (Controller):
  - Scan starten, die Fortschrittsanzeige läuft durch.
  - Eine Test-Anwendung anlegen und löschen.
  - Löschen während eines laufenden Scans → 409-Meldung.
- [ ] **Step 4:** Commit `docs: describe application deletion and scan progress`.
