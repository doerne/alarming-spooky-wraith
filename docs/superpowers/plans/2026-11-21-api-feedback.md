# Rückkanal API – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Agent meldet Issue-URL/Status/Kommentar pro Anwendung+Advisory; „behoben“ wird beim nächsten SBOM-Upload überprüft.

**Spec:** `docs/superpowers/specs/2026-11-21-api-feedback-design.md`

## Global Constraints
- Branch `sbom-action`; keine neuen Abhängigkeiten; mypy strict; Komplexität ≤ 8.
- `issueUrl` nur http/https, ≤ 500 Zeichen; `comment` ≤ 2 000; Body ohne Feld → 422.
- `make check` nach jeder Task; vor jedem Commit `fullstack-standards:architecture-reviewer`.

## Review Focus
1. **Alte Marker-ID** (absorbierte GHSA) → Meldung landet bei der kanonischen Advisory. Test in Task 1.
2. **„behoben“ gemeldet, SBOM-Upload enthält Komponente unverändert** → wieder offen mit Kommentar. Test in Task 2.
3. **„behoben“ gemeldet, Komponente in neuer SBOM aktualisiert** → bleibt behoben (bzw. SBOM-Rückkanal übernimmt). Test in Task 2.
4. **Meldung für Anwendung ohne diese CVE / unbekannte Anwendung** → 404, nichts geändert. Test in Task 1.
5. **Issue-URL mit `javascript:` oder Zeilenumbruch** → 422; im Export nur als entschärfte Zeile. Test in Task 1/3.

---

### Task 1: Datenmodell, Use Case, Endpoint
**Files:** `domain/vulnerability.py` (`ResolutionSource`, Finding-Felder), `domain/ports.py` (`FindingRepository.save_report`, `AdvisoryAliasRepository.resolve`), `application/finding_report.py` (Use Case `ReportFindingProgress`), `application/retired_findings.py` (`resolved_by=sbom`), `infrastructure/{models,repositories}.py`, Migration `ad5e2f7a4b6c_finding_report.py`, `presentation/cves_router.py`, Fakes, Tests.

```python
class ResolutionSource(StrEnum): SBOM = "sbom"; REPORTED = "reported"
Finding.issue_url: str = ""; Finding.resolved_by: ResolutionSource | None = None
FindingRepository.resolve(finding_id, status, resolved_at, resolution, resolved_by: ResolutionSource) -> None
FindingRepository.save_report(finding: Finding) -> None   # status, comment, issue_url, resolved_* übernehmen
AdvisoryAliasRepository.resolve(alias_id: str) -> str | None
@dataclass(frozen=True) class ProgressReport: status: FindingStatus | None; issue_url: str | None; comment: str | None
class ReportFindingProgress:
    def __init__(self, uow, clock) -> None
    def execute(self, *, application_id: int, advisory_id: str, report: ProgressReport) -> tuple[str, int]  # (kanonische ID, Anzahl)
```
- [ ] Failing tests (Use Case + API + Repo), umsetzen, Migration + `alembic check`, `make check`, Commit `feat: let agents report issue links and status per CVE`.

### Task 2: Nachweis beim SBOM-Upload
**Files:** `application/sbom_use_cases.py`, Tests `tests/unit/test_sbom_use_cases.py`.
- Für `to_keep`-Komponenten: Treffer mit `FIXED` + `REPORTED` → `save_report` mit `OPEN`, geleerter Auflösung, angehängtem Kommentar.
- [ ] Failing tests `test_reported_fix_reopens_when_component_still_shipped`, `test_reported_fix_stays_when_component_upgraded`, `test_sbom_fix_is_not_reopened`; umsetzen; Commit `feat: verify reported fixes against the next SBOM version`.

### Task 3: Export-Anleitung und Abschluss
**Files:** `presentation/issue_export_markdown.py`, `application/issue_export.py` (`IssueDraft.issue_urls`), Doku.
- Anleitung: `curl -X PATCH …/cves/<advisory-id> -H 'Content-Type: application/json' -d '{"issueUrl": "…"}'` nach dem Anlegen, `{"status": "behoben"}` nach dem Schließen; Basis-URL `http://127.0.0.1:8000` als Platzhalter `<cve-radar>` mit Hinweis.
- Issue-Text: Abschnitt „Vorhandenes Issue“ mit entschärften URLs, wenn vorhanden.
- [ ] Failing tests, umsetzen, echter Durchlauf per `curl`, Abschluss-Review, Commit `feat: describe the feedback API in the issue export`.
