# Findings-Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Funde-Tabellen im Dashboard und im Inventar nach Schweregrad, Status, Anwendung, Ökosystem und Freitext filtern; Kacheln/Diagramm bleiben ungefiltert.

**Architecture:** `ListFindings` bekommt ein `FindingFilter` und liefert Treffer plus Gesamtzahl im Anwendungs-Scope; `GET /api/cves` mappt Query-Parameter darauf. Im Frontend generische Filterbausteine in `shared/components` (Mehrfach-Toggle, Suchfeld mit Verzögerung), fachliche Filterleisten je Feature.

**Tech Stack:** FastAPI Query-Listen, TanStack Query, shadcn `toggle-group` + `select` (neu, über vorhandenes `radix-ui`).

**Spec:** `docs/superpowers/specs/2026-11-01-findings-filter-design.md`

## Global Constraints

- Werte eines Filters ODER, verschiedene Filter UND; `q` case-insensitive in Advisory-ID, CVE-ID, Titel, Komponentenname; Ökosystem-Sonderwert `none`.
- Sortierung bleibt Risk Score absteigend. Kacheln und Diagramm ungefiltert.
- Keine neuen npm-/Python-Abhängigkeiten; shadcn-Komponenten nur per `npx shadcn@latest add`, `src/shared/ui` nie anfassen.
- Features importieren sich nicht gegenseitig; Test-IDs nach Schema; `make check` grün je Task.

## Review Focus

1. **Suchtext mit Sonderzeichen/Leerzeichen** (`"  CVE-2024 "`, `%`, `_`) → wird getrimmt, als Text gesucht, kein Fehler (Task 1 `test_query_is_trimmed_and_literal`).
2. **Unbekannter Filterwert** in der URL → 422, nicht 500 (Task 2 `test_unknown_severity_is_422`).
3. **Filter ergibt nichts** → Hinweis + Zurücksetzen statt leerer Tabelle (Task 4 „zeigt leeren Zustand“).
4. **Schnelles Tippen** → nur eine Anfrage nach der Pause (Task 3 `useDebouncedValue`-Test).
5. **Komponente gelöscht/Anwendung leer** → Filter über leere Liste liefert `0 von 0` ohne Fehler (Task 1 `test_empty_scope`).

---

### Task 1: Filter im Use Case

**Files:** Modify `backend/app/application/list_findings.py`; Test `backend/tests/unit/test_list_findings.py`

**Interfaces:**
- `@dataclass(frozen=True) FindingFilter`: `application_id: int | None = None`, `severities: frozenset[Severity] = frozenset()`, `statuses: frozenset[FindingStatus] = frozenset()`, `ecosystems: frozenset[str] = frozenset()` (OSV-Name oder `NO_ECOSYSTEM = "none"`), `query: str = ""`
- `@dataclass(frozen=True) FindingList`: `items: list[FindingView]`, `unfiltered_total: int` (Anzahl im Anwendungs-Scope vor den übrigen Filtern)
- `ListFindings(uow).execute(finding_filter: FindingFilter = FindingFilter()) -> FindingList`
- [ ] **Step 1: Failing tests:** `test_filter_by_severity` (kritisch+hoch ODER), `test_filter_by_status`, `test_filter_by_ecosystem_and_none`, `test_filters_combine_with_and`, `test_query_matches_id_title_component_case_insensitive`, `test_query_is_trimmed_and_literal` (`"  react  "` trifft; `"%"` trifft nichts), `test_unfiltered_total_respects_application_scope`, `test_empty_scope`. Bestehende Tests auf `.items` umstellen.
- [ ] **Step 2:** FAIL. **Step 3:** Implementieren (kleine Prädikat-Funktionen, Komplexität ≤ 8). **Step 4:** `make check-backend` grün. **Step 5:** Commit `feat: filter findings in use case`.

### Task 2: Filter in der API

**Files:** Modify `backend/app/presentation/cves_router.py`; Test `backend/tests/api/test_cve_radar_api.py`

**Interfaces:** `GET /api/cves?severity=&status=&ecosystem=&application_id=&q=` – `severity: list[Severity]`, `status: list[FindingStatus]`, `ecosystem: list[Ecosystem | Literal["none"]]` (je `Query(default=[])`), `q: str = ""`. Antwort `{items, total, unfilteredTotal}`.
- [ ] **Step 1: Failing tests:** `test_filter_query_params` (zwei Komponenten, `severity=kritisch` → nur passende; `unfilteredTotal` = alle), `test_multiple_values_are_or`, `test_unknown_severity_is_422`, `test_ecosystem_none`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementieren. **Step 4:** `make check-backend` grün. **Step 5:** Commit `feat: filter findings via API`.

### Task 3: Generische Filterbausteine (shared)

**Files:** `npx shadcn@latest add toggle-group select` (in `frontend/`); Create `src/shared/components/multi-toggle-filter.tsx`, `src/shared/components/search-input.tsx`, `src/shared/hooks/use-debounced-value.ts` + Tests

**Interfaces:**
- `MultiToggleFilter<T extends string>({ label, options: {value: T, label: string}[], selected: T[], onChange(values: T[]), testIdPrefix })` – shadcn `ToggleGroup type="multiple"`; Items `${testIdPrefix}-${value}`; Gruppe `testIdPrefix` (muss 3-teilig sein, z. B. `cves-select-severity`).
- `SearchInput({ value, onChange(value), placeholder, testId })` – Input mit Lupe-Icon, `aria-label`.
- `useDebouncedValue<T>(value: T, delayMs: number): T`.
- [ ] **Step 1: Failing tests:** Toggle meldet Mehrfachauswahl/Abwahl; SearchInput meldet Eingabe; `useDebouncedValue` liefert neuen Wert erst nach `delayMs` (fake timers).
- [ ] **Step 2–4:** FAIL → implementieren → `make check-frontend`. **Step 5:** Commit `feat: add shared filter controls`.

### Task 4: Filterleiste Dashboard

**Files:** Modify `features/cves/model/types.ts` (`FindingFilters`, Optionen-Konstanten, `findingsPageSchema` += `unfilteredTotal`), `api/cves-api.ts` (`fetchFindings(filters?: FindingFilters)` baut `URLSearchParams` mit Mehrfachwerten), `hooks/use-findings.ts` (`useFindings(filters?)`, Key `["findings", filters ?? "all"]`, `placeholderData: keepPreviousData`), `cves-page.tsx`; Create `components/findings-filter-bar.tsx` (+ Test), `components/filter-summary.tsx`
- `FindingFilters`: `severities: RiskLevel[]`, `statuses: string[]`, `ecosystems: string[]`, `applicationId: number | null`, `query: string`; `EMPTY_FILTERS`.
- Anwendungs-Optionen aus den ungefilterten Funden (eindeutige `applicationName`/ID – dafür `applicationId` in `FindingResponse` ergänzen, Backend Task 2 mit erledigen); Ökosystem-Optionen: feste OSV-Liste + „ohne“.
- Test-IDs: `cves-form-filters`, `cves-select-severity(-<wert>)`, `cves-select-status`, `cves-select-ecosystem`, `cves-select-application`, `cves-input-search`, `cves-btn-reset-filters`, `cves-text-filter-summary`, `cves-text-no-results`.
- [ ] **Step 1: Failing tests:** Filterleiste meldet Änderungen; Zurücksetzen leert; Summary „12 von 83 Funden“; „zeigt leeren Zustand“; Seite: Kacheln nutzen ungefilterte Daten (App-Test mit gemocktem fetch: Filter setzen → Kachel „Funde gesamt“ unverändert, Tabellen-Request trägt `severity=`).
- [ ] **Step 2–4.** **Step 5:** Commit `feat: filter findings on the dashboard`.

### Task 5: Filter im Inventar-CVE-Reiter

**Files:** Modify `features/inventory/api/inventory-api.ts`, `hooks/use-application-findings.ts`, `components/detail-tabs.tsx`, `application-detail-page.tsx`, `model/types.ts`; Create `components/application-cve-filters.tsx` (+ Test)
- Gleiche Filter ohne Anwendung; nutzt die shared-Bausteine; eigene Optionen-Konstanten im Inventar (Feature-Grenze) – Ruling notieren.
- Test-IDs mit Präfix `inventory-` analog Task 4.
- [ ] **Step 1: Failing tests** (Filter melden, leerer Zustand, Summary). **Step 2–4.** **Step 5:** Commit `feat: filter findings of an application`.

### Task 6: Abschluss
- [ ] Browser-Prüfung (Dashboard + Inventar, 390 px). `make check`. `architecture-reviewer` + Abschluss-Review; Befunde beheben.
