# Kennzahlen zur Abarbeitung – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Schwachstellen-Seite und CVE-Tab einer Anwendung zeigen Fristen (überfällig/bald fällig), die lohnendsten Paket-Updates und die Aufteilung „Wie erledigt“.

**Architecture:** Neue reine Domain-Datei `remediation.py` (Fristen, Update-Ziele, Art der Erledigung). Versionen vergleicht ein neuer Port `VersionComparator`, implementiert von `UniversVersionMatcher`. Use Case `GetRemediationKpis` und Endpoint `GET /api/findings/kpis`. Der Verlauf bekommt `closedByOutcome`. Im Frontend liegen die drei reinen Karten in `shared/components`, je Feature ein Query-Hook unter den bestehenden Schlüsseln.

**Tech Stack:** FastAPI, Pydantic v2, univers (vorhanden) · React, TanStack Query, zod, shadcn/ui (`card`, `chart`), recharts (vorhanden).

**Spec:** `docs/superpowers/specs/2026-11-22-remediation-kpis-design.md`

## Global Constraints

- **Erledigt** = `behoben`, `akzeptiert`, `false_positive`. **Offener Bestand** = `offen` + `in_arbeit`.
- Fristen: kritisch 7, hoch 30, mittel 90, niedrig 180 Tage. `DEADLINE_START = 2026-11-22 00:00 UTC`. Fristbeginn = `max(first_seen_at, DEADLINE_START)`, `None` → `DEADLINE_START`. Überfällig: `due_at <= now`. Bald fällig: `now < due_at <= now + 7 Tage`.
- Art der Erledigung (`ClosureKind`): `fixed_confirmed` (behoben, `resolved_by=sbom`), `fixed_reported` (behoben, `reported`), `fixed_manual` (behoben, ohne Quelle), `accepted`, `false_positive`. UI-Texte: „Behoben, bestätigt“, „Behoben, gemeldet“, „Behoben, von Hand“, „Akzeptiert“, „False Positive“.
- Fix-Version gilt nur, wenn `is_newer(ecosystem, fixed_version, found_version)`. Gruppierung nach (Ökosystem, Paketname), Zielversion = höchste gültige Fix-Version, Limit 5, Sortierung nach Anzahl Funde absteigend, dann Paketname.
- Keine neuen Abhängigkeiten. Keine Änderungen in `frontend/src/shared/ui/`. Nur semantische Farben und `--chart-*`-Tokens.
- Test-IDs `<feature>-<element>-<zweck>`, kebab-case.
- Python: mypy strict, Komplexität ≤ 8, ≤ 5 Parameter. TS: strict, kein `any`, ≤ 4 Parameter.
- Kommentare auf Deutsch, Bezeichner Englisch, UI-Texte Deutsch.
- Nach jeder Task `make check` grün; vor jedem Commit Subagent `fullstack-standards:architecture-reviewer` (macht der Controller).
- Commit-Format `feat: …` / `fix: …` / `refactor: …`, Trailer:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` und
  `Claude-Session: https://claude.ai/code/session_01HoSCtHbaSEToQC55z1Hq5A`.

## Review Focus

1. **Frist genau erreicht** (`due_at == now`) zählt als überfällig, nicht als bald fällig (Task 1).
2. **Altfund mit `first_seen_at` vor dem 22.11.** (BASELINE) wird erst ab 22.11. gerechnet; ein hoher Altfund ist am 22.12. 00:00 UTC überfällig (Task 1).
3. **Fix-Version ≤ eingesetzter Version oder unlesbar** → Fund zählt nicht als behebbar, Paket erscheint ohne gültigen Fund nicht (Task 2, Task 3).
4. **Summe `closedByOutcome` = `closedTotal`** auch mit Altfunden, deren `closed_at < first_seen_at` (Task 4).
5. **Anwendung ohne offene Funde**: Fristen-Karte „Keine offenen Funde.“, Update-Karte Leerzustand, Wie-erledigt-Karte bei 0 Leerzustand – kein leerer Chart (Task 6).

---

### Task 1: Domain – Art der Erledigung und Fristen

**Files:**
- Create: `backend/app/domain/remediation.py`
- Test: `backend/tests/unit/test_remediation.py`

**Interfaces:**
- Produces:
  - `class ClosureKind(StrEnum)`: `FIXED_CONFIRMED="fixed_confirmed"`, `FIXED_REPORTED="fixed_reported"`, `FIXED_MANUAL="fixed_manual"`, `ACCEPTED="accepted"`, `FALSE_POSITIVE="false_positive"`
  - `def closure_kind_of(finding: Finding) -> ClosureKind | None` (None für offenen Bestand)
  - `DEADLINE_DAYS: dict[Severity, int]`, `DEADLINE_START: datetime`, `DUE_SOON_DAYS = 7`
  - `def due_at(finding: Finding) -> datetime`
  - `@dataclass(frozen=True) class DeadlineSummary: overdue: int; due_soon: int; overdue_by_severity: dict[Severity, int]; next_due_at: datetime | None`
  - `def compute_deadlines(findings: Sequence[Finding], now: datetime) -> DeadlineSummary` (nur offener Bestand; `overdue_by_severity` immer alle vier Stufen; `next_due_at` = frühestes `due_at` der nicht überfälligen offenen Funde, sonst None)

- [ ] **Step 1: Failing tests** (Helfer `make_finding` wie in `tests/unit/test_finding_trend.py`, zusätzlich `resolved_by`)

```python
NOW = datetime(2026, 12, 1, 12, 0, tzinfo=UTC)

def test_closure_kind_per_status_and_source():
    assert closure_kind_of(make_finding(FindingStatus.FIXED, resolved_by=ResolutionSource.SBOM)) == ClosureKind.FIXED_CONFIRMED
    assert closure_kind_of(make_finding(FindingStatus.FIXED, resolved_by=ResolutionSource.REPORTED)) == ClosureKind.FIXED_REPORTED
    assert closure_kind_of(make_finding(FindingStatus.FIXED)) == ClosureKind.FIXED_MANUAL
    assert closure_kind_of(make_finding(FindingStatus.ACCEPTED)) == ClosureKind.ACCEPTED
    assert closure_kind_of(make_finding(FindingStatus.FALSE_POSITIVE)) == ClosureKind.FALSE_POSITIVE
    assert closure_kind_of(make_finding(FindingStatus.IN_PROGRESS)) is None

def test_due_at_starts_at_deadline_start_for_old_or_unknown_first_seen():
    old = make_finding(first_seen_at=datetime(2025, 11, 1, tzinfo=UTC), level=Severity.HOCH)
    assert due_at(old) == datetime(2026, 12, 22, tzinfo=UTC)
    assert due_at(make_finding(first_seen_at=None, level=Severity.KRITISCH)) == datetime(2026, 11, 29, tzinfo=UTC)

def test_due_at_uses_first_seen_after_start():
    seen = datetime(2026, 11, 25, 8, 0, tzinfo=UTC)
    assert due_at(make_finding(first_seen_at=seen, level=Severity.MITTEL)) == seen + timedelta(days=90)

def test_exactly_due_counts_as_overdue_not_due_soon():
    finding = make_finding(first_seen_at=NOW - timedelta(days=7), level=Severity.KRITISCH)
    summary = compute_deadlines([finding], NOW)
    assert (summary.overdue, summary.due_soon) == (1, 0)
    assert summary.overdue_by_severity == {Severity.KRITISCH: 1, Severity.HOCH: 0, Severity.MITTEL: 0, Severity.NIEDRIG: 0}

def test_due_soon_window_and_next_due():
    soon = make_finding(first_seen_at=NOW - timedelta(days=25), level=Severity.HOCH)   # fällig in 5 Tagen
    later = make_finding(first_seen_at=NOW - timedelta(days=10), level=Severity.HOCH)  # fällig in 20 Tagen
    summary = compute_deadlines([later, soon], NOW)
    assert (summary.overdue, summary.due_soon) == (0, 1)
    assert summary.next_due_at == NOW + timedelta(days=5)

def test_closed_findings_never_count_and_in_progress_does():
    overdue_closed = make_finding(FindingStatus.ACCEPTED, first_seen_at=NOW - timedelta(days=60), level=Severity.KRITISCH)
    overdue_working = make_finding(FindingStatus.IN_PROGRESS, first_seen_at=NOW - timedelta(days=60), level=Severity.KRITISCH)
    assert compute_deadlines([overdue_closed, overdue_working], NOW).overdue == 1

def test_no_open_findings():
    summary = compute_deadlines([], NOW)
    assert (summary.overdue, summary.due_soon, summary.next_due_at) == (0, 0, None)
```

- [ ] **Step 2:** `cd backend && uv run pytest tests/unit/test_remediation.py -v` → FAIL (Modul fehlt).
- [ ] **Step 3:** `remediation.py` umsetzen (Docstring/Kommentare deutsch).
- [ ] **Step 4:** Tests grün, `make check` grün.
- [ ] **Step 5:** Commit `feat: compute finding deadlines and closure kinds`.

### Task 2: Domain – Port `VersionComparator` und Update-Ziele

**Files:**
- Modify: `backend/app/domain/ports.py`, `backend/app/domain/remediation.py`
- Modify: `backend/tests/fakes.py` (Fake-Vergleicher)
- Test: `backend/tests/unit/test_remediation.py`

**Interfaces:**
- Produces:
  - `class VersionComparator(Protocol): def is_newer(self, ecosystem: str | None, candidate: str, current: str) -> bool: ...` (True nur, wenn beide lesbar und `candidate > current`)
  - `@dataclass(frozen=True) class OpenItem: package_name: str; ecosystem: str | None; found_version: str; fixed_version: str | None; application_name: str`
  - `@dataclass(frozen=True) class UpdateTarget: package_name: str; ecosystem: str | None; target_version: str; findings: int; applications: int`
  - `@dataclass(frozen=True) class UpdateSummary: targets: list[UpdateTarget]; fixable_open: int; open_total: int; more_packages: int`
  - `UPDATE_TARGET_LIMIT = 5`
  - `def compute_update_targets(items: Sequence[OpenItem], versions: VersionComparator, limit: int = UPDATE_TARGET_LIMIT) -> UpdateSummary`
  - `tests/fakes.py`: `class TupleVersionComparator` – vergleicht Punkt-Zahlen numerisch (`"1.10.0" > "1.9.0"`), Unlesbares → False.

- [ ] **Step 1: Failing tests**

```python
VERSIONS = TupleVersionComparator()

def item(package="lodash", found="4.17.0", fixed="4.17.21", app="A", ecosystem="npm"):
    return OpenItem(package, ecosystem, found, fixed, app)

def test_groups_by_package_and_takes_highest_valid_fix():
    summary = compute_update_targets([item(fixed="4.17.12"), item(fixed="4.17.21", app="B"), item(fixed="4.17.19")], VERSIONS)
    assert summary.targets == [UpdateTarget("lodash", "npm", "4.17.21", 3, 2)]
    assert (summary.fixable_open, summary.open_total, summary.more_packages) == (3, 3, 0)

def test_fix_not_newer_or_missing_is_not_fixable():
    summary = compute_update_targets([item(found="5.0.0", fixed="4.17.21"), item(fixed=None), item(fixed="kaputt")], VERSIONS)
    assert summary.targets == []
    assert (summary.fixable_open, summary.open_total) == (0, 3)

def test_same_name_in_other_ecosystem_is_separate_package():
    summary = compute_update_targets([item(), item(ecosystem="PyPI", found="1.0", fixed="2.0")], VERSIONS)
    assert len(summary.targets) == 2

def test_sorted_by_findings_then_name_and_limited():
    items = [item(package=f"p{index}") for index in range(6)] + [item(package="z"), item(package="z")]
    summary = compute_update_targets(items, VERSIONS, limit=5)
    assert [target.package_name for target in summary.targets] == ["z", "p0", "p1", "p2", "p3"]
    assert summary.more_packages == 2
```

- [ ] **Step 2:** Tests rot.
- [ ] **Step 3:** Port, Domain-Funktion und Fake umsetzen.
- [ ] **Step 4:** Tests grün, `make check` grün.
- [ ] **Step 5:** Commit `feat: rank package updates by fixable open findings`.

### Task 3: Infrastruktur – `UniversVersionMatcher.is_newer`

**Files:**
- Modify: `backend/app/infrastructure/univers_matcher.py`
- Test: `backend/tests/unit/test_univers_matcher.py`

**Interfaces:**
- Consumes: `VersionComparator` (Task 2)
- Produces: `UniversVersionMatcher.is_newer(ecosystem, candidate, current) -> bool` – gleiche Versionsklasse je Ökosystem wie `is_affected` (`_VERSION_CLASS`, Fallback `DebianVersion`), `_parse` wiederverwenden.

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.parametrize(("ecosystem", "candidate", "current", "expected"), [
    ("npm", "1.10.0", "1.9.0", True),
    ("npm", "1.2.0", "1.2.0-rc.1", True),
    ("npm", "1.2.0", "1.2.0", False),
    ("PyPI", "78.1.1", "70.3.0", True),
    ("Maven", "2.0", "2.0.1", False),
    (None, "2.10", "2.9", True),
    ("npm", "kaputt", "1.0.0", False),
    ("npm", "1.x", "1.0.0", False),
])
def test_is_newer(ecosystem, candidate, current, expected):
    assert _MATCHER.is_newer(ecosystem, candidate, current) is expected
```

- [ ] **Step 2:** rot · **Step 3:** umsetzen · **Step 4:** grün + `make check`
- [ ] **Step 5:** Commit `feat: compare versions per ecosystem for update targets`.

### Task 4: Verlauf – `closed_by_outcome`

**Files:**
- Modify: `backend/app/domain/finding_trend.py`, `backend/app/presentation/trend_router.py`
- Test: `backend/tests/unit/test_finding_trend.py`, `backend/tests/api/test_finding_trend_api.py`

**Interfaces:**
- Consumes: `ClosureKind`, `closure_kind_of` (Task 1)
- Produces: `FindingTrend.closed_by_outcome: dict[ClosureKind, int]` (alle fünf Schlüssel), gezählt über dieselbe Menge wie `closed_total` (verfolgbare Funde, `closed_at` im Zeitraum). DTO-Feld `closedByOutcome` mit den `ClosureKind`-Werten als Schlüssel.

- [ ] **Step 1: Failing tests**
  - Unit: zwei Funde im Zeitraum erledigt (behoben/SBOM, akzeptiert), einer vor dem Zeitraum erledigt, ein Altfund mit `closed_at < first_seen_at` → `closed_by_outcome[FIXED_CONFIRMED] == 1`, `[ACCEPTED] == 1`, Rest 0, `sum(values) == closed_total`.
  - API: `set(body["closedByOutcome"]) == {"fixed_confirmed", "fixed_reported", "fixed_manual", "accepted", "false_positive"}`.
- [ ] **Step 2–4:** rot → umsetzen → grün + `make check`.
- [ ] **Step 5:** Commit `feat: break down closed findings by how they were closed`.

### Task 5: Use Case und Endpoint `GET /api/findings/kpis`

**Files:**
- Create: `backend/app/application/remediation_kpis.py`, `backend/app/presentation/kpis_router.py`
- Modify: `backend/app/presentation/app_factory.py` (`AppServices.version_comparator: VersionComparator | None = None`, `app.state.version_comparator`, Router registrieren), `backend/app/main.py` (vorhandenes `versions` übergeben)
- Test: `backend/tests/unit/test_remediation_kpis.py`, `backend/tests/api/test_remediation_kpis_api.py`

**Interfaces:**
- Consumes: `compute_deadlines`, `compute_update_targets`, `OpenItem`, `VersionComparator`
- Produces:
  - `@dataclass(frozen=True) class RemediationKpis: deadlines: DeadlineSummary; updates: UpdateSummary`
  - `GetRemediationKpis(uow: UnitOfWork, clock: Callable[[], datetime], versions: VersionComparator).execute(application_id: int | None = None) -> RemediationKpis` – Anwendung prüfen wie `GetFindingTrend` (`EntityNotFoundError` → 404); `OpenItem` aus Komponente (Name, Ökosystem `.value`, `found_version` des Funds), Advisory (`fixed_version`) und Anwendungsname; nur offener Bestand.
  - Router-Dependency `get_version_comparator(request)` liest `app.state.version_comparator` wie `get_sbom_parser`.
  - Response (camelCase über `ApiModel`): `deadlines { overdue, dueSoon, overdueBySeverity, nextDueAt }`, `updates { targets[{ packageName, ecosystem, targetVersion, findings, applications }], fixableOpen, openTotal, morePackages }`.

- [ ] **Step 1: Failing tests**
  - Unit (Fakes, `TupleVersionComparator`): zwei Anwendungen mit demselben Paket → ein Ziel mit `applications == 2`; mit `application_id` nur deren Funde; erledigte Funde fehlen in `open_total`; unbekannte Anwendung → `EntityNotFoundError`.
  - API: `/api/findings/kpis` 200 mit Schlüsseln `deadlines`, `updates`; `?applicationId=<bekannt>` 200; `?applicationId=999` 404. Client mit `AppServices(clock=…, version_comparator=TupleVersionComparator())`.
- [ ] **Step 2–4:** rot → umsetzen → grün + `make check`.
- [ ] **Step 5:** Commit `feat: expose remediation KPIs endpoint`.

### Task 6: Frontend shared – Typen, Query-Keys, drei Karten

**Files:**
- Create: `frontend/src/shared/api/remediation-kpis.ts`, `frontend/src/shared/api/query-keys.ts`
- Modify: `frontend/src/shared/api/finding-trend.ts` (`closedByOutcome`)
- Create: `frontend/src/shared/components/deadline-card.tsx`, `update-targets-card.tsx`, `closure-breakdown-card.tsx` (+ je `.test.tsx`)
- Modify: alle Stellen mit den String-Literalen `["findings"]`, `["application-findings", id]`, `["application", id]` in `features/**/hooks` → Konstanten aus `query-keys.ts` (reiner Refactor, Verhalten gleich)

**Interfaces:**
- Produces:
  - `remediationKpisSchema`, `type RemediationKpis`, `fetchRemediationKpis({ applicationId?: number })` → `GET /api/findings/kpis[?applicationId=]`
  - `CLOSURE_KINDS = ["fixed_confirmed","fixed_reported","fixed_manual","accepted","false_positive"] as const`, `CLOSURE_KIND_LABELS` (UI-Texte aus Global Constraints)
  - `queryKeys.findings = ["findings"] as const`, `queryKeys.applicationFindings(id)`, `queryKeys.application(id)`
  - `DeadlineCard({ deadlines, feature })`: Test-IDs `${feature}-card-deadlines`, `${feature}-text-overdue`, `${feature}-text-due-soon`, `${feature}-text-next-due`; überfällig > 0 → `text-destructive`; ohne offenen Bestand (`openTotal === 0` über Prop `openTotal`) Text „Keine offenen Funde.“; Datum lokal `TT.MM.`.
  - `UpdateTargetsCard({ updates, feature, showApplications })`: `${feature}-card-update-targets`, `${feature}-list-update-targets`, `${feature}-item-update-target-${index}`, `${feature}-text-fixable`; Zeile „X von Y offenen Funden durch Update behebbar“; bei `morePackages > 0` „+ N weitere Pakete“; ohne Ziele „Kein offener Fund mit bekannter Fix-Version.“
  - `ClosureBreakdownCard({ closedByOutcome, feature })`: `${feature}-card-closure-breakdown`, `${feature}-item-closure-${kind}`; Summe 0 → „Im Zeitraum nichts erledigt.“; sonst gestapelte Leiste/Balken mit `--chart-1..5` und Zahlen je Art.

- [ ] **Step 1:** Komponententests (Vitest, `getByTestId`): je Karte Normalfall, Leerzustand, `text-destructive` bei überfällig > 0, Spalte „Anwendungen“ nur bei `showApplications`, „+ 2 weitere Pakete“, Schema-Test für `fetchRemediationKpis` (URL mit/ohne `applicationId`).
- [ ] **Step 2–4:** rot → umsetzen → grün + `make check`.
- [ ] **Step 5:** Commit `feat: add shared remediation KPI cards`.

### Task 7: Seiten einbinden

**Files:**
- Create: `frontend/src/features/cves/hooks/use-remediation-kpis.ts` (Key `[...queryKeys.findings, "kpis"]`), `frontend/src/features/inventory/hooks/use-application-kpis.ts` (Key `[...queryKeys.applicationFindings(id), "kpis"]`)
- Modify: `frontend/src/features/cves/cves-page.tsx`, `frontend/src/features/inventory/application-cves-page.tsx` (+ Tests)

**Interfaces:**
- Consumes: Task 6.
- Layout: nach Verlauf/Schweregrad eine Reihe `grid gap-6 lg:grid-cols-3` mit `DeadlineCard`, `ClosureBreakdownCard` (aus `trend.data.closedByOutcome`), `UpdateTargetsCard` (`showApplications` nur auf der Schwachstellen-Seite). Fehler → `<p role="alert" className="text-sm text-destructive" data-testid="cves-error-kpis">Kennzahlen konnten nicht geladen werden.</p>` bzw. `inventory-error-kpis`. Laden → nichts.

- [ ] **Step 1:** Seiten-Tests: Karten erscheinen nach Laden; KPI-Request mit `applicationId=<id>` (per `URLSearchParams` prüfen); Fehlerhinweis bei 500.
- [ ] **Step 2–4:** rot → umsetzen → grün + `make check`.
- [ ] **Step 5:** Commit `feat: show deadlines, update targets and closure breakdown`.

### Task 8: Abschluss

- [ ] **Step 1:** README: Abschnitt „Verlauf“ um Fristen (Tage je Schweregrad, Start 22.11.2026), „Wie erledigt“ und „Behebbar durch Update“ ergänzen.
- [ ] **Step 2:** `make check` grün.
- [ ] **Step 3:** Backend neu bauen (`make dev-services`), beide Seiten im Browser prüfen (hell/dunkel, Anwendung ohne Funde).
- [ ] **Step 4:** Commit `docs: describe remediation KPIs`.
