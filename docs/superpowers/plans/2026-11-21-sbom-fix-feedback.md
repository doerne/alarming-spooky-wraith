# Rückkanal SBOM – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Treffer ausgebauter SBOM-Komponenten werden beim nächsten erfolgreichen Scan „behoben“ oder auf den Nachfolger-Treffer übertragen.

**Architecture:** Neue Felder an Component/Finding; Upload markiert statt zu löschen; ein Use Case `ResolveRetiredFindings` läuft am Ende von `RunIngest`.

**Spec:** `docs/superpowers/specs/2026-11-21-sbom-fix-feedback-design.md`

## Global Constraints
- Branch `sbom-action`, keine neuen Abhängigkeiten, mypy strict, Komplexität ≤ 8.
- Kein Auflösen, wenn ein Quell-Ergebnis `RunStatus.ERROR` hat.
- `false_positive` bleibt beim Auflösen; offen / in_arbeit / akzeptiert → behoben.
- `make check` nach jeder Task; vor jedem Commit `fullstack-standards:architecture-reviewer`.

## Review Focus
1. **Upgrade ohne Fix** (alte und neue Version betroffen) → alter Treffer verschwindet, neuer trägt Status/Kommentar, nichts „behoben“. Test in Task 2.
2. **Quelle fällt im Scan aus** → keine Auflösung, ausgebaute Treffer bleiben offen. Test in Task 2.
3. **Zwei Uploads vor dem nächsten Scan** (v2 baut aus, v3 baut weitere aus) → alle ausgebauten werden aufgelöst, Text nennt die jeweilige Version. Test in Task 2.
4. **Neuer Upload bringt die Komponente zurück** → neue Live-Komponente, alter Treffer wird beim Scan auf sie übertragen. Test in Task 2.
5. **MariaDB-Fremdschlüssel** (component.retired_in_version_id → sbom_version; DeleteSbom) → Löschreihenfolge stimmt. Test in Task 1 (SQLite mit FK).

---

### Task 1: Datenmodell, Upload, Ausblenden
**Files:** `domain/inventory.py`, `domain/vulnerability.py`, `domain/ports.py`, `application/sbom_use_cases.py`, `application/inventory_use_cases.py` (GetApplication), `application/ingest.py` (nur Live), `infrastructure/{models,repositories}.py`, Migration `9c4d1e6f3a5b_retired_components.py`, `tests/fakes.py`, Tests.

**Interfaces – Produces:**
```python
Component.retired_in_version_id: int | None = None
Component.is_retired -> bool  (property)
Finding.resolved_at: datetime | None = None
Finding.resolution: str = ""
ComponentRepository.retire_many(component_ids: Sequence[int], version_id: int) -> None
FindingRepository.resolve(finding_id: int, status: FindingStatus, resolved_at: datetime, resolution: str) -> None
```
- Upload: `to_remove` aufteilen – mit Treffern → `retire_many(ids, version.id)`, ohne → wie bisher löschen. Abgleich nur gegen Live-Komponenten (`not is_retired`).
- `DeleteSbom` entfernt Treffer + alle Komponenten der SBOM (inkl. ausgebauter) **vor** den Versionen.
- `RunIngest` und `GetApplication` ignorieren ausgebaute Komponenten.

- [ ] Failing tests: `test_removed_component_with_findings_is_retired`, `test_removed_component_without_findings_is_deleted`, `test_reconcile_ignores_retired_components`, `test_get_application_hides_retired_components`, `test_ingest_skips_retired_components`, `test_delete_sbom_removes_retired_components` (+ FK-Variante in `test_repositories_foreign_keys.py`), Repo-Roundtrip der neuen Felder.
- [ ] Umsetzen, Migration + `alembic check`, `make check`, Commit `feat: retire removed SBOM components instead of deleting findings`.

### Task 2: Auflösen am Ende des Scans
**Files:** Create `application/retired_findings.py`; Modify `application/ingest.py`; Tests `tests/unit/test_retired_findings.py`, `tests/unit/test_ingest.py`.

**Interfaces – Produces:**
```python
class ResolveRetiredFindings:
    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime]) -> None
    def execute(self) -> int   # Anzahl behobener Treffer; kein Commit
```
`RunIngest.execute` ruft es nach `_persist`, nur wenn kein Ergebnis `RunStatus.ERROR` hat.
`resolution` = `f"Komponente ausgebaut mit SBOM {sbom.name} {version.label}"`.

- [ ] Failing tests: `test_resolves_to_fixed_when_cve_gone`, `test_keeps_false_positive`, `test_transfers_triage_to_successor` (Review Focus 1, 4), `test_cleans_up_retired_component_without_findings`, `test_mentions_retiring_version` (Review Focus 3), Ingest: `test_ingest_resolves_after_successful_run`, `test_ingest_does_not_resolve_when_a_source_failed` (Review Focus 2).
- [ ] Umsetzen, `make check`, echter Durchlauf (Upload → Scan → Status), Commit `feat: mark findings of retired components as fixed after the next scan`.

### Task 3: Abschluss
- [ ] Doku-Absatz in `docs/local-development.md` (SBOM-Abschnitt), Abschluss-Review, Funde beheben.
