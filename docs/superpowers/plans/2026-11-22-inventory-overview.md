# Inventar-Übersicht mit Kennzahlen – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Inventar-Seite zeigt vier Summen-Kacheln und eine sortier- und filterbare Tabelle mit Kennzahlen je Anwendung („wo brennt es“, „ist alles gepflegt“).

**Architecture:**
- Ein neuer Domain-Baustein `application_overview` enthält die Regeln für Scan-Zustand und SBOM-Alter.
- Der Use Case `GetApplicationsOverview` lädt Anwendungen, Komponenten und Funde je einmal, gruppiert sie im Speicher und liefert sie über `GET /api/applications/overview`.
- Im Frontend sortieren und filtern reine Modellfunktionen. Die Seite `inventory-page.tsx` holt die Daten, Kacheln, Tabelle und Anlege-Dialog sind reine Komponenten.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2 · React, TanStack Query, zod, shadcn/ui (`table`, `card`, `dialog`, `badge`, `button`), lucide-react.

**Spec:** `docs/superpowers/specs/2026-11-22-inventory-overview-design.md`

## Global Constraints

- **Kacheln:**
  - Texte: „Mit kritischen Funden“, „Mit überfälligen Fristen“, „SBOM veraltet oder fehlt“, „Seit Änderung nicht gescannt“.
  - Bei einem Wert über 0 steht „brennt“ (kritisch, überfällig) in `text-destructive`. „Pflege“ (SBOM, nicht gescannt) bekommt das Icon `TriangleAlert` in normaler Textfarbe.
  - Es ist höchstens ein Filter aktiv, die aktive Kachel trägt `aria-pressed`.
- **SBOM veraltet:** Es gibt keine SBOM, oder die neueste Version ist älter als `SBOM_STALE_AFTER_DAYS = 30` Tage.
- **Scan-Zustand:**
  - `never_scanned`: Es gab noch keinen verwertbaren Lauf.
  - `changed_since_scan`: `inventory_changed_at` liegt echt nach dem Beginn des letzten verwertbaren Laufs.
  - Sonst `current`.
- **Zählregeln:**
  - Offen und überfällig zählen alle nicht erledigten Funde der Anwendung, auch auf ausgebauten Komponenten, wie bei `ListFindings` und `GetRemediationKpis`.
  - Komponenten zählen nur aktive (`not is_retired`).
- **Tabellentexte:**
  - Spalten: „Anwendung“, „Offen“, „Überfällig“, „Komponenten“, „SBOM“, „Gescannt“, „GitHub“.
  - Leere Werte: „keine“ (0 offene Funde), „keine SBOM“, „aktuell“, „seit TT.MM. geändert“, „Noch kein Scan“, „–“ (kein Repository).
  - SBOM-Alter: „heute“, „vor 1 Tag“, „vor N Tagen“.
  - Leerzustände: „Noch keine Anwendung angelegt.“ und „Keine Anwendung in dieser Auswahl.“, dazu der Button „Filter zurücksetzen“.
- **Kopf:** Überschrift „Inventar“, Button „Anwendung anlegen“ (Icon `Plus`) mit Dialog. Darunter einmal die vorhandene `ScanFreshness`-Zeile.
- **Regeln:**
  - Keine neuen Abhängigkeiten, keine Änderungen an `frontend/src/shared/ui/` und `src/index.css`.
  - Nur semantische Farben.
  - Test-IDs folgen `<feature>-<element>-<zweck>`.
  - Python: mypy strict, Komplexität ≤ 8, ≤ 5 Parameter. TS: strict, kein `any`, Komplexität ≤ 8, ≤ 4 Parameter.
  - Kommentare deutsch, Bezeichner englisch, UI-Texte deutsch.
- **Ablauf:**
  - Nach jeder Task `make check` grün. Vor jedem Commit startet der Controller `fullstack-standards:architecture-reviewer`.
  - Commits im Format `feat: …` / `fix: …` / `refactor: …` / `docs: …` mit den Trailern
    `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` und
    `Claude-Session: https://claude.ai/code/session_01HoSCtJrCXxzpny7usdBciw`.

## Review Focus

1. **Anwendung ganz ohne Daten** (keine Komponenten, Funde oder SBOM): Die Zeile zeigt „keine“, „0“, „keine SBOM“. Sie zählt bei „SBOM veraltet oder fehlt“ (Task 2, Task 4).
2. **Erledigte Funde** (behoben, akzeptiert, false positive) zählen weder offen noch überfällig. Ein offener Fund auf einer ausgebauten Komponente zählt mit (Task 2).
3. **Noch nie ein verwertbarer Scan:** Alle Anwendungen stehen auf `never_scanned`. Gibt es einen Scan, aber kein `inventory_changed_at`, ist die Anwendung `current` (Task 1).
4. **Gleichstand beim Sortieren:** Bei gleichen Werten entscheidet der Name aufsteigend, in beide Richtungen (Task 4).
5. **Route `overview` gegen `/{application_id}`:** `GET /api/applications/overview` darf nicht als ID gelesen werden (422 oder 404) (Task 3).

---

### Task 1: Domain – Regeln der Übersicht

**Files:**
- Create: `backend/app/domain/application_overview.py`
- Test: `backend/tests/unit/test_application_overview.py`

**Interfaces:**
- Produces:
  - `SBOM_STALE_AFTER_DAYS: int = 30`
  - `class ScanState(StrEnum)`: `CURRENT = "current"`, `CHANGED_SINCE_SCAN = "changed_since_scan"`, `NEVER_SCANNED = "never_scanned"`
  - `def scan_state(inventory_changed_at: datetime | None, last_usable_scan_started_at: datetime | None) -> ScanState`
  - `def is_sbom_stale(latest_upload_at: datetime | None, now: datetime) -> bool`
  - `@dataclass(frozen=True) class ApplicationOverview` mit den Feldern `application_id: int`, `name: str`, `description: str`, `open_by_severity: dict[Severity, int]` (immer alle vier Stufen), `overdue: int`, `component_count: int`, `latest_sbom_upload_at: datetime | None`, `sbom_stale: bool`, `scan_state: ScanState`, `inventory_changed_at: datetime | None`, `github_repository: str | None`

- [ ] **Step 1: Failing tests**
  - `test_without_usable_scan_is_never_scanned`: `scan_state(None, None)` und `scan_state(T, None)` ergeben `NEVER_SCANNED`.
  - `test_unchanged_inventory_is_current`: `scan_state(None, S) == CURRENT`, `scan_state(S, S) == CURRENT` (gleich ist nicht „danach“).
  - `test_change_after_scan_start_is_changed`: `scan_state(S + 1 s, S) == CHANGED_SINCE_SCAN`.
  - `test_missing_sbom_is_stale`: `is_sbom_stale(None, NOW) is True`.
  - `test_sbom_stale_after_thirty_days`: Upload genau 30 Tage vor `NOW` ergibt False, 30 Tage + 1 s ergibt True.
- [ ] **Step 2:** `cd backend && uv run pytest tests/unit/test_application_overview.py -q` → FAIL (Modul fehlt).
- [ ] **Step 3:** Umsetzen in `backend/app/domain/application_overview.py`, rein, nur Standardbibliothek und `app.domain.vulnerability.Severity`.
- [ ] **Step 4:** Test → PASS, dann `make check` grün.
- [ ] **Step 5:** Commit `feat: add application overview rules`.

### Task 2: Use Case `GetApplicationsOverview` und neueste SBOM je Anwendung

**Files:**
- Modify: `backend/app/domain/ports.py` (`SbomRepository`)
- Modify: `backend/app/infrastructure/repositories.py` (`SqlAlchemySbomRepository`)
- Modify: `backend/tests/fakes.py` (`InMemorySbomRepository`)
- Create: `backend/app/application/applications_overview.py`
- Test: `backend/tests/unit/test_repositories.py`, neu `backend/tests/unit/test_applications_overview.py`

**Interfaces:**
- Consumes: Task 1 (`ApplicationOverview`, `scan_state`, `is_sbom_stale`), `compute_deadlines` und `is_closed` (bestehend), `uow.scan_runs.latest_usable()` (bestehend).
- Produces:
  - `SbomRepository.latest_upload_by_application(self) -> dict[int, datetime]`: je Anwendungs-ID der späteste `uploaded_at` über alle Versionen aller ihrer SBOMs. Anwendungen ohne SBOM fehlen im Dict. Eine Abfrage (Join SBOM ↔ Version, `GROUP BY application_id`, `max(uploaded_at)`), Zeiten als UTC (`as_utc`).
  - `class GetApplicationsOverview(uow: UnitOfWork, clock: Callable[[], datetime])` mit `execute() -> list[ApplicationOverview]`, sortiert nach Name.
- Ruling für den Builder: Die Komponenten kommen aus `uow.components.list_all()`, die Funde aus `uow.findings.list()`. `application.components` nicht nutzen, je Anwendung keine Abfrage (Anti-Ziel N+1).

- [ ] **Step 1: Failing tests**
  - Repository (`test_repositories.py`, SQLite-Fixture `uow` wie die vorhandenen Tests): `test_latest_upload_by_application_takes_newest_version` mit zwei SBOMs einer Anwendung, Versionen vom 01.11. und 20.11. (über beide SBOMs verteilt) → `{app_id: 20.11.}`. Eine zweite Anwendung ohne SBOM fehlt im Dict.
  - Use Case (`test_applications_overview.py`, In-Memory-UoW, feste Uhr `NOW = 2026-11-22 10:00 UTC`):
    - `test_counts_open_findings_by_severity_and_overdue`: Anwendung „Shop“ mit einem offenen kritischen Fund (Erstsichtung vor 8 Tagen, also überfällig), einem offenen hohen Fund und einem behobenen kritischen Fund ergibt `open_by_severity == {KRITISCH: 1, HOCH: 1, MITTEL: 0, NIEDRIG: 0}` und `overdue == compute_deadlines(open_findings, NOW).overdue == 1`.
    - `test_retired_component_counts_finding_but_not_component`: Ein offener Fund auf einer ausgebauten Komponente zählt in `open_by_severity`, `component_count` zählt nur die aktive.
    - `test_application_without_data`: Eine leere Anwendung ergibt alle Zähler 0, `latest_sbom_upload_at is None`, `sbom_stale is True` und `scan_state == NEVER_SCANNED`, wenn es keinen Lauf gibt.
    - `test_scan_state_uses_last_usable_run`: Bei einem verwertbaren Lauf, gestartet um 04:00, wird eine Anwendung, die um 09:00 geändert wurde, zu `CHANGED_SINCE_SCAN`. Eine Anwendung ohne Änderung ist `CURRENT`.
    - `test_other_applications_are_separate`: Funde und SBOM der einen Anwendung erscheinen nicht bei der anderen.
- [ ] **Step 2:** Tests → FAIL.
- [ ] **Step 3:** Port, SQL-Implementierung, Fake und Use Case umsetzen. Gruppieren mit `dict[int, list[…]]`. Komplexität ≤ 8, notfalls kleine Hilfsfunktionen.
- [ ] **Step 4:** Tests → PASS, `make check` grün.
- [ ] **Step 5:** Commit `feat: compute the applications overview`.

### Task 3: Endpoint `GET /api/applications/overview`

**Files:**
- Modify: `backend/app/presentation/inventory_router.py`
- Test: neu `backend/tests/api/test_applications_overview_api.py`

**Interfaces:**
- Consumes: Task 2 (`GetApplicationsOverview`), `ClockDep` und `UnitOfWorkDep` (bestehend).
- Produces:
  - JSON-Liste, je Eintrag (camelCase über `ApiModel`): `id`, `name`, `description`, `openBySeverity` (Objekt mit `kritisch`, `hoch`, `mittel`, `niedrig`), `overdue`, `componentCount`, `latestSbomUploadAt` (ISO oder null), `sbomStale`, `scanState`, `inventoryChangedAt` (ISO oder null), `githubRepository` (oder null).
  - DTO `ApplicationOverviewResponse`.
  - Die Route steht im Router vor `@router.get("/applications/{application_id}")`.

- [ ] **Step 1: Failing tests**
  - `test_overview_lists_applications_in_camel_case`: Eine angelegte Anwendung mit einer Komponente (wie `_add_react` in `test_cve_radar_api.py`) liefert 200 und einen Eintrag mit genau den Schlüsseln oben. `openBySeverity == {"kritisch": 0, "hoch": 0, "mittel": 0, "niedrig": 0}`, `componentCount == 1`, `scanState == "never_scanned"`, `sbomStale is True`.
  - `test_overview_is_not_read_as_application_id`: `GET /api/applications/overview` liefert 200 und eine Liste, keinen 422.
- [ ] **Step 2:** Tests → FAIL (404/422).
- [ ] **Step 3:** DTO und Route umsetzen, ohne Logik im Router.
- [ ] **Step 4:** Tests → PASS, `make check` grün.
- [ ] **Step 5:** Commit `feat: expose the applications overview`.

### Task 4: Frontend – Modell, API und Hook

**Files:**
- Create: `frontend/src/features/inventory/model/overview.ts` (+ `overview.test.ts`)
- Modify: `frontend/src/features/inventory/api/inventory-api.ts`
- Create: `frontend/src/features/inventory/hooks/use-applications-overview.ts`
- Modify: `frontend/src/shared/api/query-keys.ts`, `frontend/src/features/inventory/hooks/use-create-application.ts`

**Interfaces:**
- Consumes: JSON aus Task 3.
- Produces (aus `model/overview.ts`):
  - `applicationOverviewSchema` (zod), `type ApplicationOverview`, `type OverviewSeverity = "kritisch" | "hoch" | "mittel" | "niedrig"`, `OVERVIEW_SEVERITIES` (in dieser Reihenfolge)
  - `type TileKey = "critical" | "overdue" | "sbom" | "unscanned"`
  - `summarizeOverview(rows: ApplicationOverview[]): Record<TileKey, number>` und `matchesTile(row, tile: TileKey): boolean`
  - `filterOverview(rows, tile: TileKey | null): ApplicationOverview[]`
  - `type SortKey = "name" | "open" | "overdue" | "components" | "sbom" | "scan" | "github"`, `type SortDirection = "asc" | "desc"`, `interface OverviewSort { key: SortKey; direction: SortDirection }`, `DEFAULT_OVERVIEW_SORT: OverviewSort = { key: "open", direction: "desc" }`
  - `sortOverview(rows, sort: OverviewSort): ApplicationOverview[]` (neue Liste)
  - `sbomAgeText(isoUploadedAt: string, now: Date): string` → „heute“ / „vor 1 Tag“ / „vor N Tagen“ (volle Tage)
- Produces: `listApplicationsOverview(): Promise<ApplicationOverview[]>` (Parse über das Schema) und `useApplicationsOverview()`.
- **Query-Key:** `queryKeys.applicationsOverview = ["findings", "applications-overview"] as const`.
  - Ruling: Der Key liegt unter `["findings"]` statt unter `["applications"]` wie in der Spec. Damit laden ihn alle Stellen, die heute `["findings"]` invalidieren (Scan-Ende, Triage, SBOM, Komponenten, GitHub, Löschen), automatisch neu. Die Spec verlangt genau das.
  - `useCreateApplication` invalidiert ihn zusätzlich.

- [ ] **Step 1: Failing tests** (`overview.test.ts`, Fixture-Helfer `row(overrides)`)
  - `summarizeOverview`: Drei Zeilen (kritisch 2 / überfällig 3 / SBOM aktuell / current; nur hoch / SBOM veraltet / changed; nichts / keine SBOM / never) ergeben `{critical: 1, overdue: 1, sbom: 2, unscanned: 2}`.
  - `filterOverview(rows, "sbom")` liefert die beiden SBOM-Zeilen, `filterOverview(rows, null)` alle.
  - `sortOverview` Standard: Bei Zeilen A {k0 h5}, B {k2 h0} und C {k2 h0, überfällig 1} ist die Reihenfolge C, B, A.
  - `sortOverview` Gleichstand: Bei zwei Zeilen mit gleichen Zahlen, „beta“ und „alpha“, steht `alpha` in beide Richtungen zuerst.
  - `sortOverview({key: "sbom", direction: "desc"})`: keine SBOM, dann die älteste, dann die neueste.
  - `sortOverview({key: "scan", direction: "desc"})`: `never_scanned`, dann `changed_since_scan` (ältere Änderung zuerst), dann `current`.
  - `sbomAgeText`: gleicher Tag ergibt „heute“, 1 Tag „vor 1 Tag“, 5 Tage „vor 5 Tagen“.
  - Schema: Eine Beispielantwort aus Task 3 lässt sich parsen.
- [ ] **Step 2:** `cd frontend && npx vitest run src/features/inventory/model/overview.test.ts` → FAIL.
- [ ] **Step 3:** Umsetzen. Die Vergleiche je `SortKey` stehen in einer Tabelle `Record<SortKey, Comparator>`, der Name ist immer der letzte Vergleich (aufsteigend). Komplexität ≤ 8.
- [ ] **Step 4:** Tests → PASS, `make check` grün.
- [ ] **Step 5:** Commit `feat: add applications overview model and query`.

### Task 5: Frontend – Kacheln, Tabelle, Anlege-Dialog, Seite

**Files:**
- Create: `frontend/src/features/inventory/components/overview-tiles.tsx` (+ Test)
- Create: `frontend/src/features/inventory/components/overview-table.tsx` (+ Test)
- Create: `frontend/src/features/inventory/components/create-application-dialog.tsx` (+ Test)
- Modify: `frontend/src/features/inventory/components/application-form.tsx` (bleibt das Formular, wird im Dialog genutzt)
- Modify: `frontend/src/features/inventory/inventory-page.tsx` (+ neu `inventory-page.test.tsx`)
- Delete: `frontend/src/features/inventory/components/application-list.tsx` (+ Test)
- Create: `frontend/src/shared/lib/severity.ts`; Modify: `frontend/src/features/cves/components/severity-badge.tsx` (nutzt es)

**Interfaces:**
- Consumes: Task 4 (alle Exporte aus `model/overview.ts`, `useApplicationsOverview`), `ScanFreshness` + `describeScanFreshness` und `useScanStatus` (aus `features/inventory/hooks/use-scan-status.ts`), `ClickableRow` (`shared/components`).
- Produces:
  - `shared/lib/severity.ts`: `SEVERITY_BADGE_VARIANT: Record<"kritisch" | "hoch" | "mittel" | "niedrig", "destructive" | "default" | "secondary" | "outline">`, mit denselben Werten wie heute in `severity-badge.tsx`. `SeverityBadge` importiert es von dort.
  - `OverviewTiles({ counts: Record<TileKey, number>, active: TileKey | null, onToggle: (tile: TileKey) => void })`
  - `OverviewTable({ rows, sort, now, onSort: (key: SortKey) => void, onSelect: (applicationId: number) => void })`:
    - Ein Klick auf die aktive Spalte dreht die Richtung. Eine neue Spalte startet mit `desc`, nur „Anwendung“ und „GitHub“ starten mit `asc`.
    - Den nächsten `OverviewSort` berechnet die Seite.
  - `CreateApplicationDialog({ open, onOpenChange, onCreate: (values: ApplicationInput) => void })`
- **Test-IDs:**
  - `inventory-card-tile-critical|overdue|sbom|unscanned`
  - `inventory-list-overview`, `inventory-item-app-<id>` (Zeile, über `ClickableRow`)
  - `inventory-btn-sort-<SortKey>`
  - `inventory-btn-open-create-app` (Kopf-Button), `inventory-dialog-create-app`
  - `inventory-btn-reset-filter`, `inventory-text-empty`, `inventory-text-filter-empty`, `inventory-error-overview`
- **Ruling:** Der Kopf-Button heißt `inventory-btn-open-create-app` und nicht `inventory-btn-create-app` wie in der Spec. Die vorhandene ID gehört schon dem Absende-Button im Formular und bleibt dort.

- [ ] **Step 1: Failing tests**
  - Kacheln:
    - Die Werte werden angezeigt. Kritisch 2 hat `text-destructive`, SBOM 1 zeigt ein Icon, SBOM 0 zeigt keines.
    - Ein Klick ruft `onToggle("sbom")` auf. Die aktive Kachel hat `aria-pressed="true"`.
  - Tabelle:
    - Eine Zeile zeigt Name und Beschreibung, die Zähler, „keine SBOM“, „Noch kein Scan“ und „–“.
    - `seit TT.MM. geändert` erscheint bei `changed_since_scan`.
    - Ein Klick auf `inventory-btn-sort-overdue` ruft `onSort("overdue")` auf. Der aktive Kopf hat `aria-sort="descending"`.
    - Ein Klick auf die Zeile ruft `onSelect(id)` auf.
  - Dialog: Name eingeben → Anlegen ruft `onCreate({ name: "Shop" })` auf.
  - Seite (Fetch gemockt wie `application-sboms-page.test.tsx`):
    - Die Kacheln zeigen die Summen.
    - Ein Klick auf die Kachel SBOM filtert die Tabelle, ein zweiter Klick zeigt wieder alle.
    - Ein leerer Filter zeigt `inventory-text-filter-empty`, und `inventory-btn-reset-filter` setzt ihn zurück.
    - Ohne Anwendungen erscheint `inventory-text-empty`.
    - Ein Klick auf eine Zeile öffnet die Detailansicht (`inventory-section-detail`).
- [ ] **Step 2:** Tests → FAIL.
- [ ] **Step 3:** Umsetzen.
  - Die Seite hält `tile` und `sort` als State, zeigt `Skeleton` beim Laden und `role="alert"` bei einem Fehler.
  - Über der Tabelle steht einmal `ScanFreshness` mit `describeScanFreshness({ status, now })`, so wie auf der Schwachstellen-Seite.
  - Die Kacheln nutzen `Card` und `button`, die Zähler `Badge` mit `SEVERITY_BADGE_VARIANT`.
  - `application-list.tsx` mit Test entfernen.
- [ ] **Step 4:** Tests → PASS, `make check` grün.
- [ ] **Step 5:** Commit `feat: show application stats in the inventory overview`.

### Task 6: Abschluss

- [ ] **Step 1:** README: In der Funktionstabelle „Inventar“ ergänzen um „Übersicht mit Kennzahlen je Anwendung (offene Funde, Fristen, SBOM-Alter, Scan-Stand)“. Unter „Schnellstart“ den Satz zur Inventar-Seite anpassen.
- [ ] **Step 2:** `make check` grün.
- [ ] **Step 3:** `make dev-services`, Vite starten und prüfen:
  - `GET /api/applications/overview` liefert für die echten Anwendungen plausible Zahlen. Gegenprobe: Offen und überfällig stimmen mit dem CVE-Reiter derselben Anwendung überein.
  - Im Browser, falls verfügbar: Kacheln, Filter, Sortierung, Dialog, hell und dunkel.
- [ ] **Step 4:** Commit `docs: describe the inventory overview`.
