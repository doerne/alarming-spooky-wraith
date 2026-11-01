# Spaltenfilter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Checkbox-Schritte.

**Goal:** Filter in die Spaltenüberschriften verlegen, Ökosystem-Spalte ergänzen.
**Spec:** `docs/superpowers/specs/2026-11-01-column-filters-design.md`

## Global Constraints
Keine neuen Abhängigkeiten (nur `npx shadcn add popover`); `shared/ui` nie anfassen und nicht
formatieren; Feature-Grenzen; Test-IDs kebab-case; `make check` grün je Task.

## Review Focus
1. 0 Treffer → Tabelle + Kopf-Filter bleiben bedienbar (Task 3 „leere Zeile mit Zurücksetzen“).
2. Suche in Auswahlliste ohne Treffer → Hinweis statt leerer Liste (Task 2).
3. Tastatur: Kopf-Filter per Tab/Enter öffnen, Esc schließt (Task 2, Radix-Popover).
4. Mehrere Anwendungen gewählt → ODER (Task 1 `test_filter_by_several_applications`).
5. Advisory-Suche trifft nicht die Komponente und umgekehrt (Task 1 `test_column_queries_are_separate`).

### Task 1: Backend – getrennte Suche + mehrere Anwendungen
`FindingFilter` += `application_ids: frozenset[int]`, `advisory_query: str`, `component_query: str`;
`GET /api/cves` += `application` (mehrfach, int), `advisory`, `component`.
Tests: `test_filter_by_several_applications`, `test_column_queries_are_separate`, API-Test der Parameter.
Commit `feat: filter findings by column queries and several applications`.

### Task 2: Shared Kopf-Filter
`npx shadcn@latest add popover`. Create `shared/components/column-filter.tsx`:
`ColumnFilter<T>({ label, options, selected, onChange, searchable?, testIdPrefix })` – Button in der
Überschrift (Label + Filter-Icon, Zähler `selected.length`), Popover mit optionalem Suchfeld,
Checkbox-Liste, „Auswahl löschen“; `ColumnSearch({ label, value, onChange, testId })` – Label +
kompaktes Suchfeld in der Überschrift. Alte `multi-toggle-filter.tsx` + Test löschen, wenn ungenutzt.
Tests: Auswahl/Abwahl, Suche filtert Optionen, „keine Treffer“-Hinweis, Zähler, Löschen.
Commit `feat: add column header filters`.

### Task 3: Dashboard-Tabelle
`FindingFilters` → `severities, statuses, ecosystems, applicationIds: number[], advisoryQuery, componentQuery`;
`buildFindingsQuery` angepasst; `CvesTable` Props `filters, applications, onFiltersChange, onReset`;
Kopfzeile mit Filtern, neue Spalte Ökosystem (`-` ohne), leere Zeile `cves-text-no-results` +
`cves-btn-reset-no-results`. `findings-filter-bar.tsx` entfernen; Seite: Summary/Reset darüber, Suche verzögert.
Tests anpassen/ergänzen (Tabelle, App-Test). Commit `feat: filter findings in the table header`.

### Task 4: Inventar-Tabelle
Gleiches Muster ohne Anwendung; `application-cve-filters.tsx` entfernen, Ökosystem-Spalte.
Commit `feat: filter application findings in the table header`.

### Task 5: Abschluss
Browser (Dashboard, Inventar, 390 px, Tastatur), `make check`, architecture-reviewer + Abschluss-Review, Fix-Pass.
