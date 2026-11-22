# Advisories über Aliase zusammenführen – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pro Schwachstelle genau eine Advisory, auch ohne CVE-ID; vorhandene Duplikate heilen beim nächsten Scan.

**Architecture:** Gruppierung und kanonische ID als reine Funktionen in `advisory_merge.py`; Bereinigung im Ingest (`_persist_advisory`) über neue Repository-Methoden; neue Tabelle `advisory_alias`.

**Tech Stack:** Python 3.13, SQLAlchemy 2, Alembic.

**Spec:** `docs/superpowers/specs/2026-11-21-advisory-alias-merge-design.md`

## Global Constraints
- Branch `sbom-action`, keine neuen Abhängigkeiten, mypy strict, Komplexität ≤ 8.
- Kanonische ID: kleinste `CVE-` → kleinste `GHSA-` → kleinste ID.
- Status-Übernahme nur, wenn der kanonische Treffer `offen` ist. Kommentare mit `"\n\n"` verbinden.
- Nach jeder Task `make check`; vor jedem Commit `fullstack-standards:architecture-reviewer`.

## Review Focus
1. **Kette A↔B, B↔C ohne direkte Verbindung A↔C** → eine Gruppe. Test in Task 1.
2. **Alias-Advisory hat Treffer für dieselbe Komponente wie die kanonische** → kein Unique-Fehler (`uq_finding_advisory_component`), Triage bleibt. Test in Task 2.
3. **Eine GHSA bekommt später eine CVE-ID** → GHSA-Advisory wird in die CVE überführt, Alias-Tabelle zeigt auf die CVE. Test in Task 2.
4. **Alias-ID, unter der keine Advisory existiert** → nur Alias-Zeile, kein Fehler. Test in Task 2.
5. **MariaDB-Fremdschlüssel** (finding → advisory) → Treffer werden vor dem Löschen der Advisory umgehängt/gelöscht. Test in Task 2 (SQLite mit `PRAGMA foreign_keys=ON`).

---

### Task 1: Gruppierung und kanonische ID

**Files:** Modify `backend/app/application/advisory_merge.py`, `backend/app/application/ingest.py` (`_persist` gruppiert über `group_hits`); Test `backend/tests/unit/test_advisory_merge.py`.

**Interfaces – Produces:**
```python
def identity_ids(vuln: SourceVuln) -> frozenset[str]          # id + aliases
def canonical_key(ids: Iterable[str]) -> tuple[str, str | None]  # (advisory_id, cve_id)
def group_by_identity[T](items: Sequence[T], ids_of: Callable[[T], frozenset[str]]) -> list[list[T]]
MergedAdvisory.aliases: tuple[str, ...]                         # Gruppe ohne kanonische ID, sortiert
```
`merge_vulns` nutzt `canonical_key` über alle Vulns der Gruppe. `advisory_key` entfällt (Aufrufer umstellen).

- [ ] Failing tests: `test_groups_direct_aliases`, `test_groups_transitively` (Review Focus 1), `test_keeps_unrelated_apart`, `test_canonical_prefers_cve_then_ghsa_then_min`, `test_merge_lists_aliases_without_canonical`, bestehende `advisory_key`-Tests auf `canonical_key` umstellen.
- [ ] Umsetzen, `make check`, Commit `feat: group advisories by aliases`.

### Task 2: Bereinigung, Alias-Tabelle, Migration

**Files:** Modify `domain/ports.py`, `application/unit_of_work.py`, `application/ingest.py`, `infrastructure/{models,repositories,unit_of_work,okf_store}.py`, `tests/fakes.py`; Create Migration `backend/migrations/versions/8b3c0d5e2f4a_advisory_alias.py`; Tests `tests/unit/test_ingest.py`, `tests/unit/test_repositories.py`, `tests/unit/test_okf_store.py`.

**Interfaces – Produces:**
```python
AdvisoryRepository.find(advisory_id: str) -> Advisory | None
AdvisoryRepository.delete(advisory_id: str) -> None
FindingRepository.list_for_advisory(advisory_id: str) -> list[Finding]
FindingRepository.reassign(finding_id: int, advisory_id: str) -> None
FindingRepository.save_triage(finding_id: int, status: FindingStatus, comment: str) -> None
FindingRepository.delete(finding_id: int) -> None
AdvisoryAliasRepository.save(alias_id: str, advisory_id: str) -> None
AdvisoryAliasRepository.resolve(alias_id: str) -> str | None
AdvisoryStore.delete(advisory_id: str) -> None                 # fehlende Datei ist kein Fehler
UnitOfWork.advisory_aliases: AdvisoryAliasRepository
```
Modell `AdvisoryAliasModel` (`advisory_alias`: `alias_id` String(ADVISORY_ID_MAX_LENGTH) PK, `advisory_id` String(ADVISORY_ID_MAX_LENGTH)), ohne FK (Alias-Ziel kann später selbst umziehen). Bereinigung als Klasse `AliasAbsorber(uow, store)` in `application/alias_absorber.py` mit `absorb(canonical_id: str, aliases: Sequence[str]) -> None`, aufgerufen in `_persist_advisory` nach dem Upsert der Advisory.

- [ ] Failing tests:
  - `test_absorber_moves_findings_and_deletes_alias`, `test_absorber_merges_triage_into_open_canonical` (Review Focus 2), `test_absorber_keeps_canonical_status_when_not_open`, `test_absorber_records_alias_without_advisory` (Review Focus 4), `test_ingest_merges_ghsa_and_pysec_into_one_finding`, `test_ingest_moves_ghsa_into_later_cve` (Review Focus 3);
  - Repository: `test_finding_reassign_save_triage_delete`, `test_advisory_find_delete`, `test_advisory_alias_save_resolve_overwrites`, alles mit `PRAGMA foreign_keys=ON` (Review Focus 5);
  - OKF: `test_delete_removes_file_and_ignores_missing`.
- [ ] Umsetzen, Migration von Hand + `alembic check` gegen MariaDB, `make check`, Commit `feat: absorb alias advisories into canonical ones`.

### Task 3: Abschluss
- [ ] `make dev-services`, Scan auslösen (`POST /api/ingest/run`), prüfen: kein `PYSEC-2026-4320` mehr, `GHSA-6q48-6c7w-9gw2` mit Quellen osv + pypa, Export ohne Doppel-Abschnitt.
- [ ] Abschluss-Review des Branch-Abschnitts, Funde beheben.
