# Offene Funde im Fokus und Verlauf – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tabellen starten mit Status „Offen“; Kacheln und ein Wochen-Verlauf zeigen Zulauf neuer Funde und Abarbeitung – insgesamt und je Anwendung.

**Architecture:** Neue Spalte `finding.closed_at`, gepflegt über eine Domain-Regel. Eine reine Domain-Funktion `compute_trend` aggregiert Funde zur Abfragezeit in ISO-Wochen (UTC); Use Case `GetFindingTrend` + Endpoint `GET /api/findings/trend`. Im Frontend liegen Typ, Fetch und die reinen Anzeige-Komponenten in `shared/`, je Feature ein eigener Query-Hook.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, MariaDB · React, TanStack Query, zod, shadcn/ui (`card`, `chart`, `toggle-group`), recharts (vorhanden), lucide-react.

**Spec:** `docs/superpowers/specs/2026-11-22-open-findings-trend-design.md`

## Global Constraints

- **Erledigt** = `behoben`, `akzeptiert`, `false_positive`. **Offener Bestand** = `offen` + `in_arbeit`. **Unangetastet** = `offen`.
- Wochen: ISO-Wochen, Beginn Montag 00:00 UTC; die angebrochene aktuelle Woche ist die letzte.
- `weeks` ∈ {4, 12, 26, 52}, Standard 12.
- `BASELINE = Migrationszeitpunkt − 53 Wochen`.
- Keine neuen Abhängigkeiten. Keine Änderungen in `frontend/src/shared/ui/`. Nur semantische Farben/`--chart-*`-Tokens.
- Test-IDs `<feature>-<element>-<zweck>`, kebab-case.
- Python: mypy strict, Komplexität ≤ 8, ≤ 5 Parameter. TS: strict, kein `any`, ≤ 4 Parameter.
- Kommentare auf Deutsch, Bezeichner Englisch, UI-Texte Deutsch.
- Nach jeder Task `make check` grün; vor jedem Commit Subagent `fullstack-standards:architecture-reviewer`.
- Commit-Format `feat: …` / `fix: …` / `refactor: …`, Trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Wiedereröffnung**: ein erledigter Fund wird wieder `offen` → `closed_at` leer, er zählt wieder zum offenen Bestand (Test in Task 1 und Task 4).
2. **Wechsel erledigt → erledigt** (akzeptiert → behoben, auch per SBOM/GitHub-Sync) behält `closed_at` – keine doppelte Abarbeitung (Task 1, Task 2 `resolve`).
3. **Wochengrenze**: `first_seen_at` genau Montag 00:00 UTC am Zeitraumbeginn zählt als „neu“, nicht als Ausgangsbestand (Task 4).
4. **Anwendung ohne Funde / Zeitraum ohne Bewegung**: alle Wochen mit 0, Diagramm zeigt Hinweis statt leerer Fläche (Task 4, Task 6).
5. **Altfunde mit nachgetragenem `first_seen_at = BASELINE`** lösen kein Auto-Issue aus und erscheinen nie als „neu“ (Task 3, Task 4).

---

### Task 1: Domain – `closed_at`-Regel und `absorb`

**Files:**
- Modify: `backend/app/domain/vulnerability.py`
- Test: `backend/tests/unit/test_domain_model.py`

**Interfaces:**
- Produces:
  - `CLOSED_STATUSES: frozenset[FindingStatus]` = `{FIXED, ACCEPTED, FALSE_POSITIVE}`
  - `def is_closed(status: FindingStatus) -> bool`
  - `def closed_at_after(previous_status: FindingStatus, previous_closed_at: datetime | None, new_status: FindingStatus, now: datetime) -> datetime | None`
  - `Finding.closed_at: datetime | None = None` (neues Feld, hinter `first_seen_at`)
  - `Finding.with_status(self, status: FindingStatus, now: datetime) -> Finding`
  - `Finding.reopened()` setzt zusätzlich `closed_at=None`
  - `Finding.absorb(other)` übernimmt `min(first_seen_at)` (None ignorieren) und beim Statusübertrag `other.closed_at`

- [ ] **Step 1: Failing tests**

```python
NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
EARLIER = datetime(2026, 10, 1, tzinfo=UTC)

def test_closed_at_set_when_leaving_open_states():
    assert closed_at_after(FindingStatus.OPEN, None, FindingStatus.ACCEPTED, NOW) == NOW
    assert closed_at_after(FindingStatus.IN_PROGRESS, None, FindingStatus.FIXED, NOW) == NOW

def test_closed_at_kept_between_closed_states():
    assert closed_at_after(FindingStatus.ACCEPTED, EARLIER, FindingStatus.FIXED, NOW) == EARLIER

def test_closed_at_cleared_when_back_to_open_states():
    assert closed_at_after(FindingStatus.FIXED, EARLIER, FindingStatus.IN_PROGRESS, NOW) is None
    assert closed_at_after(FindingStatus.FIXED, EARLIER, FindingStatus.OPEN, NOW) is None

def test_with_status_applies_rule():  # Fund mit status OPEN → with_status(FALSE_POSITIVE, NOW).closed_at == NOW

def test_reopened_clears_closed_at():  # Fund FIXED, closed_at=EARLIER → reopened().closed_at is None

def test_absorb_keeps_earliest_first_seen():
    # self.first_seen_at=NOW, other.first_seen_at=EARLIER → merged.first_seen_at == EARLIER
    # self.first_seen_at=None, other=EARLIER → EARLIER

def test_absorb_takes_donor_closed_at_with_status():
    # self OPEN; other ACCEPTED, closed_at=EARLIER → merged.status == ACCEPTED, merged.closed_at == EARLIER

def test_absorb_keeps_own_closed_at_when_not_open():
    # self FIXED closed_at=NOW; other ACCEPTED closed_at=EARLIER → merged.closed_at == NOW
```

- [ ] **Step 2: Run** `cd backend && uv run pytest tests/unit/test_domain_model.py -v` → FAIL (ImportError `closed_at_after`).
- [ ] **Step 3: Implement** the interfaces above in `vulnerability.py`.
- [ ] **Step 4: Run** same command → PASS; dann `make check`.
- [ ] **Step 5: Commit** `feat: track when a finding was closed in the domain`

---

### Task 2: Persistenz – Spalte, Migration, Repository, Fakes

**Files:**
- Modify: `backend/app/infrastructure/models.py` (`FindingModel.closed_at`)
- Create: `backend/migrations/versions/f4c9d3e7a2b1_finding_closed_at.py` (`down_revision = "e3b8c5d2f6a1"`)
- Modify: `backend/app/infrastructure/repositories.py` (Mapper ~Z. 136–141, `resolve`, `save_report`)
- Modify: `backend/tests/fakes.py` (`InMemoryFindingRepository.resolve`, `save_report` unverändert ok)
- Test: `backend/tests/unit/test_repositories.py`, `backend/tests/unit/test_fakes.py`

**Interfaces:**
- Consumes: `closed_at_after`, `Finding.closed_at` (Task 1)
- Produces: `FindingRepository.resolve` setzt `closed_at = closed_at_after(alter Status, altes closed_at, resolution.status, resolution.resolved_at)`; `save_report` schreibt `closed_at` und `first_seen_at` aus dem `Finding`; Mapper liest `closed_at` via `as_utc`.

- [ ] **Step 1: Failing tests** (Repository gegen die bestehende Test-DB-Fixture, gleiche Fälle für den Fake in `test_fakes.py`):

```python
def test_resolve_sets_closed_at_from_resolution_time(): # OPEN → resolve(FIXED, NOW) → closed_at == NOW
def test_resolve_keeps_closed_at_of_already_closed():   # ACCEPTED mit closed_at=EARLIER → resolve(FIXED, NOW) → closed_at == EARLIER
def test_save_report_persists_closed_at_and_first_seen_at(): # save_report(replace(f, closed_at=NOW, first_seen_at=EARLIER)) → list()[0] hat beide Werte
```

- [ ] **Step 2: Run** `cd backend && uv run pytest tests/unit/test_repositories.py tests/unit/test_fakes.py -v` → FAIL.
- [ ] **Step 3: Implement** Model-Spalte (`DateTime(timezone=True)`, nullable), Mapper, `resolve`, `save_report`, Fake-`resolve`.
- [ ] **Step 4: Migration** `upgrade()`:
  1. `add_column("finding", closed_at)`
  2. `baseline = datetime.now(UTC) - timedelta(weeks=53)` (als Bind-Parameter, nicht DB-Funktion)
  3. `UPDATE finding SET first_seen_at = :baseline WHERE first_seen_at IS NULL`
  4. `UPDATE finding SET closed_at = resolved_at WHERE status = 'behoben' AND resolved_at IS NOT NULL`
  5. `UPDATE finding SET closed_at = :baseline WHERE status IN ('behoben','akzeptiert','false_positive') AND closed_at IS NULL`
  `downgrade()`: nur `drop_column("finding", "closed_at")` (nachgetragene `first_seen_at` bleiben, Kommentar dazu).
- [ ] **Step 5: Verify migration** nach Skill `fullstack-standards:db-migration`: `make migrate`, dann in MariaDB prüfen: keine Zeile mit `first_seen_at IS NULL`; jede erledigte Zeile hat `closed_at`; keine offene Zeile hat `closed_at`. Downgrade/Upgrade einmal durchspielen.
- [ ] **Step 6: Run** `make check` → grün.
- [ ] **Step 7: Commit** `feat: persist closed_at and backfill finding timestamps`

---

### Task 3: Schreibpfade auf die Regel umstellen

**Files:**
- Modify: `backend/app/application/finding_report.py` (`_with_status`)
- Modify: `backend/app/application/github_sync.py` (`_mark_findings`, Zweig `MARK_ACCEPTED`)
- Test: `backend/tests/unit/test_finding_report.py`, `backend/tests/unit/test_github_sync.py`, `backend/tests/unit/test_retired_findings.py`, `backend/tests/unit/test_alias_absorber.py`

**Interfaces:**
- Consumes: `Finding.with_status`, `reopened`, `absorb` (Task 1), Repository (Task 2)
- Produces: alle Statuswechsel setzen `closed_at` korrekt. `retired_findings` und `alias_absorber` brauchen keinen Code-Umbau (laufen über `resolve` bzw. `absorb` + `save_report`), nur Tests.

- [ ] **Step 1: Failing tests**

```python
# test_finding_report.py
def test_report_accepted_sets_closed_at():          # PATCH-Use-Case status=akzeptiert → closed_at == clock()
def test_report_fixed_after_accepted_keeps_closed_at(): # akzeptiert (closed_at=EARLIER) → behoben → closed_at == EARLIER, resolved_at == NOW
def test_report_in_progress_clears_closed_at():     # behoben → in_arbeit → closed_at is None, resolved_at is None
# test_github_sync.py
def test_issue_closed_not_planned_sets_closed_at(): # MARK_ACCEPTED → finding.closed_at == clock()
def test_backfilled_first_seen_does_not_create_auto_issue():
    # application.auto_issue_enabled_at = NOW - 1 Tag; Fund first_seen_at = NOW - 53 Wochen → Sync legt kein Issue an
# test_retired_findings.py
def test_transfer_keeps_donor_closed_at_and_first_seen(): # Spender akzeptiert, closed_at=EARLIER, first_seen=EARLIER → Nachfolger hat beide Werte
# test_alias_absorber.py
def test_absorb_alias_keeps_earliest_first_seen():
```

- [ ] **Step 2: Run** `cd backend && uv run pytest tests/unit/test_finding_report.py tests/unit/test_github_sync.py tests/unit/test_retired_findings.py tests/unit/test_alias_absorber.py -v` → neue Tests FAIL.
- [ ] **Step 3: Implement**
  - `_with_status(finding, status, now)`: FIXED-Zweig wie bisher, zusätzlich über `with_status(FIXED, now)`; Nicht-FIXED-Zweig: `with_status(status, now)` und Auflösungsfelder (`resolved_at`, `resolved_by`, `resolution`) leeren wie bisher `reopened()` – **ohne** `closed_at` pauschal zu löschen.
  - `github_sync` MARK_ACCEPTED: `finding.with_note(note).with_status(FindingStatus.ACCEPTED, self._clock())`.
- [ ] **Step 4: Run** → PASS; `make check` grün.
- [ ] **Step 5: Commit** `feat: set closed_at on every status change`

---

### Task 4: Domain – Verlaufsberechnung

**Files:**
- Create: `backend/app/domain/finding_trend.py`
- Test: `backend/tests/unit/test_finding_trend.py`

**Interfaces:**
- Consumes: `Finding`, `FindingStatus`, `Severity`, `is_closed` (Task 1)
- Produces:

```python
TREND_WEEK_OPTIONS: tuple[int, ...] = (4, 12, 26, 52)
DEFAULT_TREND_WEEKS = 12

@dataclass(frozen=True)
class TrendWeek:
    week_start: date
    new: int
    closed: int
    open_at_end: int

@dataclass(frozen=True)
class FindingTrend:
    weeks: list[TrendWeek]
    open_at_start: int
    new_total: int
    closed_total: int
    untouched_now: int
    in_progress_now: int
    open_by_severity_now: dict[Severity, int]  # immer alle vier Stufen

def compute_trend(findings: Sequence[Finding], now: datetime, weeks: int) -> FindingTrend
```

Algorithmus: `range_start` = Montag 00:00 UTC der Woche von `now` minus `(weeks − 1)` Wochen. Pro Woche `[start, start+7d)`: `new` = `first_seen_at` im Intervall; `closed` = `closed_at` im Intervall; `open_at_end` = `first_seen_at < Ende` und (`closed_at is None` oder `closed_at ≥ Ende`). `open_at_start` analog mit `range_start`. Funde ohne `first_seen_at` überspringen. `*_now` und `open_by_severity_now` aus dem Status (`offen`/`in_arbeit`), nach `risk.level`.

- [ ] **Step 1: Failing tests** (`now = Sonntag 2026-11-22 09:00 UTC`, dessen Woche beginnt `2026-11-16`)

```python
def test_week_starts_are_mondays_ending_with_current_week():
    trend = compute_trend([], NOW, 4)
    assert [w.week_start for w in trend.weeks] == [date(2026,10,26), date(2026,11,2), date(2026,11,9), date(2026,11,16)]
    assert all(w.new == w.closed == w.open_at_end == 0 for w in trend.weeks)
    assert trend.open_by_severity_now == {s: 0 for s in Severity}

def test_counts_new_and_closed_per_week(): # 1 Fund first_seen 2026-11-03, closed 2026-11-17 → new in KW 11-02, closed in KW 11-16; open_at_end 1,1,0 ab 11-02
def test_first_seen_exactly_at_range_start_counts_as_new():  # first_seen = 2026-10-26T00:00Z → weeks[0].new == 1, open_at_start == 0
def test_finding_before_range_is_baseline():                 # first_seen = NOW − 53 Wochen, offen → open_at_start == 1, new_total == 0
def test_closed_before_range_is_not_counted():               # closed_at vor range_start → open_at_start == 0, closed_total == 0
def test_reopened_finding_counts_as_open():                  # status offen, closed_at None, first_seen vor Zeitraum → letzte Woche open_at_end == 1
def test_last_week_open_matches_now_counts():                # gemischte Funde → weeks[-1].open_at_end == untouched_now + in_progress_now
def test_open_by_severity_counts_only_open_states():          # kritisch offen, kritisch behoben, hoch in_arbeit → {KRITISCH:1, HOCH:1, MITTEL:0, NIEDRIG:0}
def test_totals_sum_weeks():                                 # new_total == sum(w.new), closed_total == sum(w.closed)
```

- [ ] **Step 2: Run** `cd backend && uv run pytest tests/unit/test_finding_trend.py -v` → FAIL.
- [ ] **Step 3: Implement** in kleinen Funktionen (Komplexität ≤ 8): `week_start_of(now) -> datetime`, `_week_of(...)`, `_count_open_at(findings, moment)`.
- [ ] **Step 4: Run** → PASS; `make check`.
- [ ] **Step 5: Commit** `feat: compute weekly finding trend`

---

### Task 5: Use Case und Endpoint

**Files:**
- Create: `backend/app/application/finding_trend.py`
- Create: `backend/app/presentation/trend_router.py`
- Modify: `backend/app/presentation/app_factory.py` (Router registrieren)
- Test: `backend/tests/unit/test_finding_trend_use_case.py`, `backend/tests/api/test_finding_trend_api.py`

**Interfaces:**
- Consumes: `compute_trend`, `TREND_WEEK_OPTIONS`, `DEFAULT_TREND_WEEKS` (Task 4)
- Produces:
  - `class GetFindingTrend: __init__(self, uow: UnitOfWork, clock: Callable[[], datetime])`; `execute(self, weeks: int, application_id: int | None = None) -> FindingTrend` – bei `application_id` erst `uow.applications.get(...)` (wirft `EntityNotFoundError` → 404), dann Funde dieser Anwendung.
  - `GET /api/findings/trend?weeks=12&applicationId=…` (Query-Alias camelCase `applicationId`; `weeks: Literal[4, 12, 26, 52] = 12`)
  - Response-DTOs (`ApiModel`): `TrendWeekResponse{week_start: date, new, closed, open_at_end}`, `FindingTrendResponse{weeks, open_at_start, new_total, closed_total, untouched_now, in_progress_now, open_by_severity_now: dict[Severity, int]}` → JSON wie im Spec (`weekStart` als `YYYY-MM-DD`).

- [ ] **Step 1: Failing tests**

```python
# Use Case (Fakes)
def test_trend_for_all_applications():            # zwei Anwendungen, je 1 offener Fund → untouched_now == 2
def test_trend_scoped_to_application():           # nur Funde der gewählten Anwendung
def test_trend_unknown_application_raises():      # pytest.raises(EntityNotFoundError)
# API (Muster wie tests/api/test_finding_report_api.py::_client, Clock fix)
def test_get_trend_default_twelve_weeks():        # GET /api/findings/trend → 200, len(weeks) == 12, Schlüssel weekStart/new/closed/openAtEnd, openBySeverityNow hat "kritisch".."niedrig"
def test_get_trend_rejects_unsupported_weeks():   # weeks=5 → 422
def test_get_trend_unknown_application_404():     # applicationId=999 → 404
```

- [ ] **Step 2: Run** `cd backend && uv run pytest tests/unit/test_finding_trend_use_case.py tests/api/test_finding_trend_api.py -v` → FAIL.
- [ ] **Step 3: Implement** Use Case, Router (keine Logik, nur Mapping), Registrierung.
- [ ] **Step 4: Run** → PASS; `make check`.
- [ ] **Step 5: Commit** `feat: expose finding trend endpoint`

---

### Task 6: Frontend shared – Typ, Fetch, Anzeige-Komponenten

**Files:**
- Create: `frontend/src/shared/api/finding-trend.ts`
- Create: `frontend/src/shared/lib/trend.ts` + `trend.test.ts`
- Create: `frontend/src/shared/components/trend-range-select.tsx` + Test
- Create: `frontend/src/shared/components/trend-cards.tsx` + Test
- Create: `frontend/src/shared/components/trend-chart.tsx` + Test

**Interfaces:**
- Produces:

```ts
// shared/api/finding-trend.ts
export const TREND_WEEK_OPTIONS = [4, 12, 26, 52] as const;
export type TrendWeeks = (typeof TREND_WEEK_OPTIONS)[number];
export const DEFAULT_TREND_WEEKS: TrendWeeks = 12;
export const findingTrendSchema = z.object({ weeks: z.array(z.object({ weekStart: z.string(), new: z.number(), closed: z.number(), openAtEnd: z.number() })), openAtStart: z.number(), newTotal: z.number(), closedTotal: z.number(), untouchedNow: z.number(), inProgressNow: z.number(), openBySeverityNow: z.record(z.enum(["kritisch","hoch","mittel","niedrig"]), z.number()) });
export type FindingTrend = z.infer<typeof findingTrendSchema>;
export function fetchFindingTrend(params: { weeks: TrendWeeks; applicationId?: number }): Promise<FindingTrend>;
// shared/lib/trend.ts
export function openNowOf(trend: FindingTrend): number;        // untouchedNow + inProgressNow
export function openDeltaOf(trend: FindingTrend): number;      // openNowOf − openAtStart
export function weekLabelOf(weekStart: string): string;        // "2026-11-16" → "16.11."
export function hasMovement(trend: FindingTrend): boolean;     // irgendeine Woche new/closed > 0
// Komponenten (rein, Props)
TrendRangeSelect({ value: TrendWeeks; onChange: (weeks: TrendWeeks) => void; feature: string })
TrendCards({ trend: FindingTrend; feature: string })
TrendChart({ trend: FindingTrend; feature: string })
```

Texte/IDs:
- RangeSelect (shadcn `ToggleGroup`, single): Labels „4 Wochen“, „12 Wochen“, „26 Wochen“, „52 Wochen“; `aria-label="Zeitraum"`; testid `${feature}-select-trend-range`, Items `${feature}-btn-trend-range-${weeks}`.
- Cards: „Offener Bestand“ (`${feature}-card-trend-open`, Differenz `${feature}-text-trend-open-delta` als „−2“ / „+3“ / „±0“ mit lucide `TrendingDown`/`TrendingUp`/`Minus`; Anstieg `text-destructive`, Rückgang `text-primary`, 0 `text-muted-foreground`), „Unangetastet“ (`-untouched`), „In Arbeit“ (`-in-progress`), „Neu im Zeitraum“ (`-new`), „Erledigt im Zeitraum“ (`-closed`).
- Chart: Card „Verlauf“, `ChartContainer` mit recharts `ComposedChart`: Balken `new` („Neu“) und `closed` („Erledigt“) gruppiert, Linie `openAtEnd` („Offener Bestand“); Farben aus `--chart-*`. testid `${feature}-chart-trend`. Ohne Bewegung (`!hasMovement`) stattdessen `${feature}-text-trend-empty`: „Im Zeitraum keine neuen oder erledigten Funde.“

- [ ] **Step 1: Failing tests**

```ts
// trend.test.ts
expect(openDeltaOf({...base, untouchedNow: 30, inProgressNow: 12, openAtStart: 44})).toBe(-2);
expect(weekLabelOf("2026-11-16")).toBe("16.11.");
expect(hasMovement({...base, weeks: [{weekStart:"2026-11-16", new:0, closed:0, openAtEnd:5}]})).toBe(false);
// trend-cards.test.tsx
// Rückgang: getByTestId("cves-text-trend-open-delta") hat Text "−2"; Card open zeigt "42"; new zeigt newTotal; closed zeigt closedTotal
// Anstieg: "+3"; Gleichstand: "±0"
// trend-range-select.test.tsx
// Klick auf "cves-btn-trend-range-26" ruft onChange(26)
// trend-chart.test.tsx
// mit Bewegung: getByTestId("cves-chart-trend") vorhanden; ohne: "cves-text-trend-empty" vorhanden, Chart nicht
```

- [ ] **Step 2: Run** `cd frontend && npx vitest run src/shared` → FAIL.
- [ ] **Step 3: Implement** (shadcn `toggle-group`, `card`, `chart` sind vorhanden; vorher `npx shadcn@latest search` nicht nötig).
- [ ] **Step 4: Run** → PASS; `make check`.
- [ ] **Step 5: Commit** `feat: add shared trend cards, chart and range select`

---

### Task 7: Schwachstellen-Seite umbauen

**Files:**
- Create: `frontend/src/features/cves/hooks/use-finding-trend.ts`
- Modify: `frontend/src/features/cves/cves-page.tsx`
- Modify: `frontend/src/features/cves/model/filters.ts` (`DEFAULT_FILTERS`)
- Modify: `frontend/src/features/cves/model/stats.ts` (`severityCountsOf`, `computeKpis` entfernen)
- Delete: `frontend/src/features/cves/components/section-cards.tsx` + Test (ersetzt durch `TrendCards`)
- Modify: `frontend/src/features/cves/components/severity-chart.tsx` (Titel „Offen nach Schweregrad“)
- Test: `model/filters.test.ts`, `model/stats.test.ts`, `components/severity-chart.test.tsx`, neuer `cves-page.test.tsx` falls nicht vorhanden

**Interfaces:**
- Consumes: Task 6
- Produces:
  - `useFindingTrend(weeks: TrendWeeks)` – `queryKey: ["findings", "trend", weeks]` (wird so von allen bestehenden `["findings"]`-Invalidierungen erfasst)
  - `DEFAULT_FILTERS: FindingFilters = { ...EMPTY_FILTERS, statuses: ["offen"] }`
  - `severityCountsOf(openBySeverity: Record<RiskLevel, number>): SeverityCount[]` (feste Reihenfolge wie `countBySeverity`)

Layout: Kopfzeile Titel + `IngestControl`; darunter `TrendRangeSelect`; `TrendCards`; Zeile mit `TrendChart` (breit) und `SeverityChart` (schmal, `lg:grid-cols-3`, Chart `col-span-2`); dann Tabelle. Startzustand der Tabelle `DEFAULT_FILTERS`; Zurücksetzen weiterhin `EMPTY_FILTERS`.

- [ ] **Step 1: Failing tests**

```ts
// filters.test.ts
expect(DEFAULT_FILTERS.statuses).toEqual(["offen"]);
expect(hasActiveFilters(DEFAULT_FILTERS)).toBe(true);
// stats.test.ts
expect(severityCountsOf({kritisch:3, hoch:10, mittel:0, niedrig:9}).map(e => e.count)).toEqual([3,10,0,9]);
// cves-page.test.tsx (fetch gemockt wie in bestehenden Page-/Hook-Tests)
// erster Aufruf von /api/cves enthält "status=offen"; "cves-card-trend-open" sichtbar; Klick "cves-btn-trend-range-4" lädt /api/findings/trend?weeks=4
```

- [ ] **Step 2: Run** `cd frontend && npx vitest run src/features/cves` → FAIL.
- [ ] **Step 3: Implement**; `computeKpis`/`SectionCards` und ihre Tests entfernen (kein toter Code).
- [ ] **Step 4: Run** → PASS; `make check`.
- [ ] **Step 5: Commit** `feat: focus vulnerabilities page on open findings and trend`

---

### Task 8: CVE-Tab der Anwendung

**Files:**
- Create: `frontend/src/features/inventory/hooks/use-application-trend.ts`
- Modify: `frontend/src/features/inventory/application-cves-page.tsx`
- Modify: `frontend/src/features/inventory/model/cve-filters.ts` (`DEFAULT_CVE_FILTERS`)
- Test: `model/cve-filters` Test, `components/application-cves-panel.test.tsx` bzw. neuer `application-cves-page.test.tsx`

**Interfaces:**
- Consumes: Task 6
- Produces:
  - `useApplicationTrend(applicationId: number, weeks: TrendWeeks)` – `queryKey: ["application-findings", applicationId, "trend", weeks]` (von Scan-Ende, SBOM-Änderung und Komponenten-Änderung bereits invalidiert)
  - `DEFAULT_CVE_FILTERS: CveFilters = { ...EMPTY_CVE_FILTERS, statuses: ["offen"] }`

Layout: über `ApplicationCvesPanel` ein Block mit `TrendRangeSelect`, `TrendCards`, `TrendChart` (`feature="inventory"`). Startfilter `DEFAULT_CVE_FILTERS`; Optionen weiter aus `EMPTY_CVE_FILTERS`-Abfrage; Zurücksetzen `EMPTY_CVE_FILTERS`.

- [ ] **Step 1: Failing tests**

```ts
expect(DEFAULT_CVE_FILTERS.statuses).toEqual(["offen"]);
// Page-Test: Abfrage der Funde enthält status=offen; "inventory-card-trend-open" sichtbar; Trend-Request enthält applicationId=<id>
```

- [ ] **Step 2: Run** `cd frontend && npx vitest run src/features/inventory` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS; `make check`.
- [ ] **Step 5: Commit** `feat: show trend and open findings first per application`

---

### Task 9: Abschluss

- [ ] **Step 1:** README-Abschnitt zur Schwachstellen-Seite um „Startfilter Offen“, Kacheln und Verlauf ergänzen (Begriffe „erledigt“/„offener Bestand“ wie Global Constraints).
- [ ] **Step 2:** `make check` → grün.
- [ ] **Step 3:** App per Skill `run` starten, beide Seiten im Browser prüfen (hell/dunkel, Zeitraumwechsel, leere Anwendung).
- [ ] **Step 4:** `architecture-reviewer`, dann Commit `docs: describe open findings focus and trend`.
