# CVE-Export für KI / GitHub-Issues – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pro Anwendung eine Markdown-Datei mit allen offenen CVEs als Issue-Vorlagen (ein Abschnitt pro CVE, nach Risiko sortiert, mit Marker) herunterladen bzw. per `curl` abrufen.

**Architecture:** Ein Use Case sammelt offene Treffer der Anwendung, gruppiert pro Advisory und reichert mit dem gespeicherten Advisory-Dokument an. Ein reiner Markdown-Renderer in `presentation` formatiert, ein Endpoint liefert `text/markdown` als Download. Das Frontend bekommt nur einen Download-Link.

**Tech Stack:** FastAPI, Pydantic v2 · React, shadcn/ui (`Button asChild`), lucide-react.

**Spec:** `docs/superpowers/specs/2026-11-21-ai-issue-export-design.md`

## Global Constraints

- Branch `sbom-action`. Keine neuen Abhängigkeiten.
- Clean Architecture laut `CLAUDE.md`: Use Case kennt nur domain/Ports; Markdown-Formatierung in `presentation`; Router ohne Fachlogik.
- Python mypy strict, Komplexität ≤ 8, ≤ 5 Parameter; TS ohne `any`, Komplexität ≤ 8.
- Exportiert werden nur Status `offen` und `in_arbeit`. Tabellenfilter gelten nicht.
- Grenzen: Beschreibung gekürzt auf **4 000** Zeichen, höchstens **10** Referenzen.
- Marker exakt: `<!-- cve-radar:application=<id>;advisory=<advisory-id> -->`.
- Titel exakt: `[<score>] <cve_id oder advisory_id> – <komponente> <version>`, bei mehreren Komponenten `… – <erste> <version> u. a.`.
- Labels: `security`, `risk:<stufe>`.
- Dateiname: `cve-issues-<slug>-<YYYY-MM-DD>.md`, Slug = Anwendungsname klein, nicht `[a-z0-9]` → `-`, zusammengefasst, Ränder entfernt; leer → `anwendung`.
- Nach jeder Task `make check` grün; vor jedem Commit Subagent `fullstack-standards:architecture-reviewer`.

## Review Focus

1. **Beschreibung enthält selbst ``` oder `<!--`** → Issue-Codeblock bricht nicht, Marker bleibt der einzige `cve-radar`-Kommentar. Test in Task 2.
2. **Advisory ohne CVE-ID und ohne Advisory-Datei** → Titel nutzt Advisory-ID, Beschreibung aus der DB, Begründung aus dem CVSS berechnet. Test in Task 1.
3. **Anwendungsname mit Umlauten/Leerzeichen/nur Sonderzeichen** → gültiger Dateiname. Test in Task 2.
4. **Treffer anderer Anwendungen zur selben CVE** → tauchen nicht im Export auf. Test in Task 1.
5. **Unbekannte Anwendung** → 404, kein leerer Export. Test in Task 1 und Task 2.

---

### Task 1: Use Case `ExportApplicationIssues`

**Files:**
- Create: `backend/app/application/issue_export.py`
- Test: `backend/tests/unit/test_issue_export.py`

**Interfaces:**
- Consumes: `UnitOfWork`, `AdvisoryStore.read_document`, `compute_risk_score` (`app/application/risk_score.py`).
- Produces:
  ```python
  EXPORTED_STATUSES = frozenset({FindingStatus.OPEN, FindingStatus.IN_PROGRESS})
  DESCRIPTION_MAX_LENGTH = 4_000
  REFERENCES_MAX = 10

  @dataclass(frozen=True)
  class AffectedComponent:
      name: str; found_version: str; ecosystem: str | None
      source: str          # "manuell" oder SBOM-Name
      status: FindingStatus; comment: str

  @dataclass(frozen=True)
  class IssueDraft:
      advisory_id: str; cve_id: str | None; title: str
      risk_score: int; risk_level: Severity; rationale: str
      cvss_base: float | None; fix_version: str | None
      description: str     # bereits gekürzt
      references: tuple[str, ...]   # höchstens 10
      components: tuple[AffectedComponent, ...]   # Score absteigend

  @dataclass(frozen=True)
  class IssueExport:
      application_id: int; application_name: str; generated_at: datetime
      issues: tuple[IssueDraft, ...]   # Score absteigend, dann advisory_id

  class ExportApplicationIssues:
      def __init__(self, uow: UnitOfWork, store: AdvisoryStore, clock: Callable[[], datetime]) -> None
      def execute(self, application_id: int) -> IssueExport   # EntityNotFoundError bei unbekannter Anwendung
  ```
- Regeln: Treffer mit `application_id` und Status in `EXPORTED_STATUSES`, deren Komponente noch existiert. Risiko des Drafts = Treffer mit höchstem Score. `rationale` aus `document.rationale`, wenn nicht leer, sonst `compute_risk_score(advisory.cvss_base).rationale`. Beschreibung aus dem Dokument, sonst `advisory.description`; länger als 4 000 → auf 4 000 kürzen und `…` anhängen. Referenzen aus dem Dokument, sonst `advisory.references`. `source` = `"manuell"` bei `sbom_id is None`, sonst `uow.sboms.get(sbom_id).name`.

- [ ] **Step 1: Failing tests** (Fakes aus `tests/fakes.py`, `FakeAdvisoryStore.documents` direkt befüllen):
  - `test_exports_only_open_and_in_progress_findings`: drei Treffer offen / in_arbeit / behoben → zwei Drafts.
  - `test_groups_components_per_advisory_with_highest_risk`: CVE-1 an react (Score 50) und an react aus SBOM `backend-image` (Score 90) → ein Draft, `risk_score == 90`, `components[0].source == "backend-image"`, `components[1].source == "manuell"`.
  - `test_sorts_by_score_then_advisory_id`.
  - `test_ignores_findings_of_other_applications` (Review Focus 4).
  - `test_falls_back_without_document` (Review Focus 2): kein Dokument, `cve_id=None`, CVSS 9.8 → `description == advisory.description`, `rationale` nicht leer.
  - `test_truncates_description_and_references`: 5 000 Zeichen, 12 Referenzen → Länge 4 001 mit `…`, 10 Referenzen.
  - `test_unknown_application_raises` (Review Focus 5).
  - `test_empty_export_has_no_issues`.
- [ ] **Step 2:** `cd backend && uv run pytest tests/unit/test_issue_export.py -q` → FAIL (ImportError).
- [ ] **Step 3:** Umsetzen in kleinen Funktionen.
- [ ] **Step 4:** Tests → PASS; `make check`.
- [ ] **Step 5: Commit** `feat: collect open CVEs of an application for issue export`

### Task 2: Markdown-Renderer und Endpoint

**Files:**
- Create: `backend/app/presentation/issue_export_markdown.py`, `backend/tests/unit/test_issue_export_markdown.py`, `backend/tests/api/test_issue_export_api.py`
- Modify: `backend/app/presentation/cves_router.py` (Endpoint), `backend/app/presentation/dependencies.py` (`ClockDep` hierher verschieben), `backend/app/presentation/sbom_router.py` (nutzt `ClockDep` aus `dependencies`)

**Interfaces:**
- Consumes: `IssueExport`, `IssueDraft` aus Task 1.
- Produces:
  ```python
  def render_issue_export(export: IssueExport) -> str
  def export_filename(export: IssueExport) -> str
  def issue_marker(application_id: int, advisory_id: str) -> str
  ```
- Endpoint: `GET /api/applications/{application_id}/cves/export` → `Response(media_type="text/markdown; charset=utf-8")`, Header `Content-Disposition: attachment; filename="<export_filename>"`.
- Aufbau der Datei:
  1. `# CVE-Issues für <Anwendung>` + Zeile „Erzeugt: <ISO-UTC> · <n> offene Schwachstellen“.
  2. `## Anleitung für die KI` mit: pro Abschnitt genau ein Issue anlegen; Titel und Labels übernehmen, Text = Inhalt des Codeblocks unverändert; vorher `gh issue list --search "cve-radar:application=<id>;advisory=<advisory-id>" --state all` und bei Treffer überspringen; fehlende Labels mit `gh label create` anlegen; in der Reihenfolge der Datei anlegen (höchstes Risiko zuerst).
  3. Pro Draft `## <n>. <Titel>`, Zeilen `**Titel:** …`, `**Labels:** security, risk:<stufe>`, dann der Issue-Text in einem Codeblock, dessen Zaun länger ist als jede Backtick-Folge im Text (mindestens ````` ```` `````, Sprache `markdown`).
  4. Leerer Export: nach der Anleitung der Satz „Keine offenen Schwachstellen.“
- Issue-Text: `## Risiko` (Score, Stufe, CVSS oder „unbekannt“, Begründung), `## Betroffene Komponenten` (Tabelle Name | Version | Ökosystem | Quelle | Status), `## Behebung` („Auf ≥ <fix> aktualisieren.“ bzw. „Kein Fix bekannt – Advisory beobachten oder Komponente ersetzen.“), `## Beschreibung`, `## Referenzen` (Liste), `## Triage-Kommentar` nur wenn ein Kommentar existiert, letzte Zeile Marker. Vorkommen von `<!--` in Beschreibung/Kommentar werden zu `&lt;!--`.

- [ ] **Step 1: Failing tests**
  - Renderer: `test_title_uses_score_cve_and_component` (`"[98] CVE-2024-1 – jinja2 3.1.4"`), `test_title_mentions_more_components` (`"… u. a."`), `test_labels_and_marker`, `test_fence_is_longer_than_backticks_in_text` (Review Focus 1: Beschreibung mit ```` ``` ```` → Zaun ```` ```` ````; genau ein `cve-radar:`-Marker), `test_html_comment_in_description_is_escaped` (Review Focus 1), `test_no_fix_known_text`, `test_empty_export_says_no_open_issues`, `test_instructions_contain_gh_search_with_marker`.
  - `export_filename`: `"Mein Shop (Prod)"` → `cve-issues-mein-shop-prod-2026-11-21.md`; `"Übersicht"` → `cve-issues-bersicht-2026-11-21.md`; `"!!!"` → `cve-issues-anwendung-2026-11-21.md` (Review Focus 3).
  - API: `test_export_returns_markdown_attachment` (Status 200, `content-type` beginnt mit `text/markdown`, `content-disposition` enthält Dateinamen, Body enthält Marker), `test_export_unknown_application_returns_404` (Review Focus 5).
- [ ] **Step 2:** Tests → FAIL.
- [ ] **Step 3:** Umsetzen; `ClockDep` nach `dependencies.py` ziehen, `sbom_router` darauf umstellen.
- [ ] **Step 4:** `make check` grün.
- [ ] **Step 5: Commit** `feat: export open CVEs as AI-ready issue markdown`

### Task 3: Frontend-Button und Abschluss

**Files:**
- Create: `frontend/src/features/inventory/components/cves-export-button.tsx`, `.test.tsx`
- Modify: `frontend/src/features/inventory/api/inventory-api.ts` (`applicationIssueExportPath(applicationId: number): string`), `frontend/src/features/inventory/application-cves-page.tsx` (Button oberhalb des Panels), `docs/local-development.md` (Abschnitt „CVEs als GitHub-Issues exportieren“ inkl. `curl`-Beispiel)

**Interfaces:**
- `CvesExportButton({ applicationId }: { applicationId: number })` – rein; `<Button asChild variant="outline">` um `<a href={path} download data-testid="inventory-btn-cves-export">` mit `FileDown`-Icon und Text „Für KI exportieren“; `title`/Beschreibung: „Offene CVEs als Markdown für GitHub-Issues“.

- [ ] **Step 1: Failing test:** Link hat `href="/api/applications/4/cves/export"`, Attribut `download` und den Text „Für KI exportieren“.
- [ ] **Step 2:** `cd frontend && npx vitest run src/features/inventory/components/cves-export-button.test.tsx` → FAIL.
- [ ] **Step 3:** Umsetzen, in `application-cves-page.tsx` einbinden, Doku ergänzen.
- [ ] **Step 4:** `make check` grün; von Hand `curl -sD- http://127.0.0.1:8000/api/applications/<id>/cves/export` gegen die laufenden Dev-Dienste (nach `make dev-services`) → 200, Markdown mit Markern.
- [ ] **Step 5: Commit** `feat: download CVE issue export in application view`
