# SBOM-Upload im Inventar – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CycloneDX-JSON-SBOMs pro Anwendung unter einem Namen versioniert hochladen; die aktuelle Version speist den CVE-Abgleich, ältere Versionen bleiben mit Komponentenliste im Archiv.

**Architecture:** Ansatz A aus dem Design. Neue Tabellen `sbom` und `sbom_version` (Momentaufnahme als JSON). Die Komponenten der aktuellen Version liegen zusätzlich als normale Zeilen in `component` (`sbom_id`, `checked`), damit Abgleich, Treffer und Filter unverändert bleiben. Ein neuer Upload gleicht diese Live-Komponenten per Schlüssel (Ökosystem, normalisierter Name, Version) ab.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, MariaDB · React, TypeScript, TanStack Query, React Hook Form + zod, shadcn/ui.

**Spec:** `docs/superpowers/specs/2026-11-21-sbom-upload-design.md`

## Global Constraints

- Branch `sbom-action`, kein neuer Branch.
- Keine neuen Abhängigkeiten (kein `python-multipart`, kein npm-Paket). Falls `npx shadcn@latest add alert-dialog` eine neue npm-Abhängigkeit eintragen will → stoppen und fragen (`radix-ui` ist schon da).
- Clean Architecture laut `CLAUDE.md`: Parser in `infrastructure`, Port in `domain`, Use Cases kennen nur `domain`, Router ohne Logik, `main.py` verdrahtet.
- Python: mypy strict, Komplexität ≤ 8, ≤ 5 Parameter. TypeScript: kein `any`, Komplexität ≤ 8, ≤ 4 Parameter.
- Kommentare/UI-Texte deutsch, Bezeichner englisch. Test-IDs `inventory-<element>-<zweck>`, mindestens drei Teile.
- `src/shared/ui/` nicht von Hand ändern. Nur semantische Farben.
- Grenzen: SBOM-Name 1–100 Zeichen, Versionsbezeichnung ≤ 100, Seriennummer ≤ 100, höchstens **50 000** Komponenten je Dokument, nginx-Upload **25m**, Komponentenname ≤ 200, Version ≤ 100.
- `specVersion` 1.4–1.7, `bomFormat == "CycloneDX"`.
- Nach jeder Task `make check` grün. Vor jedem Commit Subagent `fullstack-standards:architecture-reviewer`. Commit-Format `feat: …` / `fix: …` / `refactor: …`.

## Review Focus

1. **Gleiche Komponente mehrfach in einer SBOM** (npm-Duplikate in `node_modules`, gleicher purl) → genau eine Live-Komponente, kein Unique-Fehler, `direct` = irgendeiner direkt. Test in Task 4.
2. **PyPI-Namensvarianten** (`Jinja2` alt, `jinja2` neu; `typing_extensions` vs. `typing-extensions`) → gilt als dieselbe Komponente, Treffer bleiben. Test in Task 4.
3. **Upload für fremde/unbekannte Anwendung oder SBOM-ID einer anderen Anwendung** → 404, keine Daten verändert. Test in Task 5 (Use Case) und Task 6 (API).
4. **Ungültige Datei im Browser** (kein JSON, JSON ohne `bomFormat`, SPDX) → Fehlermeldung im Dialog, keine Anfrage. Test in Task 7.
5. **Erneuter Upload derselben Datei** → 409 mit Meldung, Archiv unverändert. Test in Task 4 und Task 6.

---

### Task 1: Domain – SBOM-Modell, Fehler, Ports, Fakes

**Files:**
- Create: `backend/app/domain/sbom.py`
- Modify: `backend/app/domain/inventory.py` (`Component`), `backend/app/domain/errors.py`, `backend/app/domain/ports.py`, `backend/app/application/unit_of_work.py`, `backend/tests/fakes.py`
- Test: `backend/tests/unit/test_domain_model.py`, `backend/tests/unit/test_fakes.py`

**Interfaces:**
- Produces (`app/domain/sbom.py`):
  ```python
  SBOM_NAME_MAX_LENGTH = 100
  SBOM_LABEL_MAX_LENGTH = 100
  SBOM_SERIAL_MAX_LENGTH = 100
  SBOM_MAX_COMPONENTS = 50_000

  @dataclass(frozen=True)
  class SbomEntry:
      name: str; version: str; category: Category; ecosystem: Ecosystem | None
      direct: bool; purl: str | None
      @property
      def checked(self) -> bool  # ecosystem is not None

  @dataclass(frozen=True)
  class ParsedSbom:
      entries: tuple[SbomEntry, ...]; serial_number: str | None
      suggested_label: str | None; skipped: int

  @dataclass
  class Sbom:
      application_id: int; name: str; id: int | None = None

  @dataclass(frozen=True)
  class SbomVersion:
      sbom_id: int; label: str; uploaded_at: datetime; serial_number: str | None
      is_current: bool; entries: tuple[SbomEntry, ...]; id: int | None = None
  ```
- `Component` bekommt am Ende `sbom_id: int | None = None` und `checked: bool = True`.
- Fehler (`errors.py`): `InvalidSbomError(InvalidValueError)`, `ConflictError(DomainError)`, `DuplicateSbomVersionError(ConflictError)`, `ComponentManagedBySbomError(ConflictError)`.
- Ports (`ports.py`):
  ```python
  class SbomParser(Protocol):
      def parse(self, document: Mapping[str, object]) -> ParsedSbom: ...
  class SbomRepository(Protocol):
      def add(self, sbom: Sbom) -> Sbom: ...
      def get(self, sbom_id: int) -> Sbom: ...            # EntityNotFoundError("SBOM", id)
      def find_by_name(self, application_id: int, name: str) -> Sbom | None: ...
      def list_for_application(self, application_id: int) -> list[Sbom]: ...
      def delete(self, sbom_id: int) -> None: ...         # inkl. aller Versionen
  class SbomVersionRepository(Protocol):
      def add(self, version: SbomVersion) -> SbomVersion: ...
      def get(self, version_id: int) -> SbomVersion: ...  # EntityNotFoundError("SBOM-Version", id)
      def current_for_sbom(self, sbom_id: int) -> SbomVersion | None: ...
      def list_for_sbom(self, sbom_id: int) -> list[SbomVersion]: ...  # neueste zuerst
      def archive(self, version_id: int) -> None: ...
  ```
  `ComponentRepository` zusätzlich `delete(component_id: int) -> None` und `list_for_sbom(sbom_id: int) -> list[Component]`; `FindingRepository` zusätzlich `delete_for_component(component_id: int) -> None`.
- `UnitOfWork` bekommt Properties `sboms: SbomRepository` und `sbom_versions: SbomVersionRepository`.
- Fakes: `InMemorySbomRepository`, `InMemorySbomVersionRepository` in `tests/fakes.py`, im `InMemoryUnitOfWork` als `sboms` / `sbom_versions`. Die neuen Komponenten-/Treffer-Methoden in den bestehenden Fakes. `InMemorySbomRepository.delete` braucht die Versionen nicht selbst zu löschen; `InMemoryUnitOfWork` übergibt dafür das Versions-Repo an das SBOM-Repo (Konstruktor `InMemorySbomRepository(versions)`), damit sich Fake und SQL gleich verhalten.

- [ ] **Step 1: Failing tests schreiben**
  - `test_sbom_entry_without_ecosystem_is_unchecked`: `SbomEntry(..., ecosystem=None, ...).checked is False`; mit `Ecosystem.NPM` → `True`.
  - `test_component_defaults_to_manual_and_checked`: `Component(...)` ohne neue Felder → `sbom_id is None`, `checked is True`.
  - `test_fake_sbom_repository_finds_by_name_per_application`: zwei SBOMs `backend` in App 1 und 2 → `find_by_name(1, "backend").application_id == 1`, `find_by_name(1, "frontend") is None`.
  - `test_fake_sbom_delete_removes_versions`: SBOM + Version anlegen, `delete` → `list_for_sbom(id) == []`, `get(id)` wirft `EntityNotFoundError`.
  - `test_fake_version_repository_lists_newest_first_and_archives`: zwei Versionen, `list_for_sbom` liefert zuletzt angelegte zuerst; nach `archive(first.id)` ist `current_for_sbom` die zweite, sofern nur sie `is_current=True` hat.
  - `test_fake_finding_delete_for_component`: zwei Treffer an Komponente 1 und 2 → nach `delete_for_component(1)` nur Treffer zu 2.
  - `test_duplicate_sbom_version_is_conflict`: `issubclass(DuplicateSbomVersionError, ConflictError)` und `issubclass(InvalidSbomError, InvalidValueError)`.
- [ ] **Step 2:** `cd backend && uv run pytest tests/unit/test_domain_model.py tests/unit/test_fakes.py -q` → FAIL (ImportError).
- [ ] **Step 3:** Domain-Dateien, Ports, UoW-Protocol und Fakes wie oben umsetzen.
- [ ] **Step 4:** Tests → PASS; `uv run ruff check .`. `uv run mypy` meldet, dass `SqlAlchemyUnitOfWork` die neuen Properties noch nicht hat – das behebt Task 2. Task 1 wird darum **ohne eigenen Commit** direkt mit Task 2 zusammen committet; ab Task 2 gilt `make check` nach jeder Task.
- [ ] **Step 5:** Kein Commit – weiter mit Task 2.

### Task 2: Persistenz – Modelle, Repositories, Migration

**Files:**
- Modify: `backend/app/infrastructure/models.py`, `backend/app/infrastructure/repositories.py`, `backend/app/infrastructure/unit_of_work.py`
- Create: `backend/migrations/versions/<rev>_sbom.py` (via `uv run alembic revision --autogenerate -m "sbom"`, `down_revision = "3c1d2e4f5a6b"`)
- Test: `backend/tests/unit/test_repositories.py`

**Interfaces:**
- Consumes: Ports aus Task 1.
- Produces: `SqlAlchemySbomRepository`, `SqlAlchemySbomVersionRepository`; `SqlAlchemyUnitOfWork.sboms` / `.sbom_versions`.
- Modelle: `SbomModel` (`sbom`: `id`, `application_id` FK `application.id`, `name` String(100), `UniqueConstraint("application_id", "name")`), `SbomVersionModel` (`sbom_version`: `id`, `sbom_id` FK `sbom.id`, `label` String(100), `uploaded_at` DateTime(timezone=True), `serial_number` String(100) nullable, `is_current` bool, `components` `JSON`). `ComponentModel` + `sbom_id` FK `sbom.id` nullable, `checked` bool `server_default=sa.true()` (Bestandsdaten → true).
- JSON-Format eines Eintrags: `{"name","version","category","ecosystem","direct","purl"}`; Abbildung in `_to_sbom_version` / `_entries_to_json`.
- `delete` von SBOM löscht zuerst `SbomVersionModel`-Zeilen, dann das SBOM (keine DB-Kaskade nötig).

- [ ] **Step 1: Failing tests** (SQLite-Fixture wie vorhanden):
  - `test_sbom_version_roundtrip_keeps_entries`: Version mit 2 Einträgen (einer ohne Ökosystem) speichern und lesen → gleiche `SbomEntry`-Tupel.
  - `test_current_for_sbom_and_archive`.
  - `test_component_roundtrip_keeps_sbom_id_and_checked`.
  - `test_delete_component_and_findings_for_component`.
  - `test_delete_sbom_removes_versions`.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Umsetzen, Migration erzeugen und durchsehen (Autogenerate muss `checked` mit `server_default` und beide neuen Tabellen enthalten, sonst nachbessern).
- [ ] **Step 4:** `make check-backend` grün; Migration gegen MariaDB: `make dev-services && make migrate`, danach `docker compose exec db mariadb … -e "DESCRIBE component; DESCRIBE sbom_version;"` zeigt die neuen Spalten (Skill `fullstack-standards:db-migration`).
- [ ] **Step 5: Commit** (Task 1 + 2) `feat: add SBOM domain model and persistence`

### Task 3: CycloneDX-Parser

**Files:**
- Create: `backend/app/infrastructure/sbom/__init__.py`, `backend/app/infrastructure/sbom/cyclonedx.py`
- Modify: `backend/app/infrastructure/sources/purl.py` (Umkehrabbildung)
- Test: `backend/tests/unit/test_cyclonedx_parser.py`

**Interfaces:**
- Consumes: `SbomEntry`, `ParsedSbom`, `InvalidSbomError`, `SBOM_MAX_COMPONENTS` aus Task 1.
- Produces: `class CycloneDxParser` mit `parse(self, document: Mapping[str, object]) -> ParsedSbom` (erfüllt `SbomParser`). In `purl.py`: `ecosystem_for_purl_type(purl_type: str) -> Ecosystem | None`.

Regeln (aus dem Spec):
- Pflicht: `bomFormat == "CycloneDX"`, `specVersion` ∈ {"1.4","1.5","1.6","1.7"}, `components` ist eine Liste; fehlt sie → `InvalidSbomError("SBOM enthält keine Komponentenliste")`.
- Rekursiv über verschachtelte `components`. Nur `type` ∈ {`library`, `framework`, `application`}; andere Typen werden still ignoriert (nicht in `skipped`).
- Ökosystem aus purl: `pkg:<type>/<namespace>/<name>@<version>`, purl-Typ über `ecosystem_for_purl_type`. Unbekannter Typ oder kein purl → `ecosystem=None`.
- Name: Maven `namespace:name`; npm mit Namespace `@scope/name` (purl kodiert `@` als `%40` → URL-dekodieren); Go `namespace/name`; sonst CycloneDX-`group` + `/` + `name` nur bei npm, sonst `name`. Bei bekanntem Ökosystem stammt der Name aus der purl, sonst aus `name`.
- Kategorie: `framework` → `Category.FRAMEWORK`, sonst `Category.LIBRARY`.
- `direct`: `bom-ref` steht in `dependsOn` des Eintrags in `dependencies`, dessen `ref == metadata.component.bom-ref`. Fehlt dieser Eintrag → alle `direct=True`.
- Übersprungen und gezählt (`skipped`): ohne `version`, Name > 200, Version > 100.
- Mehr als `SBOM_MAX_COMPONENTS` gelesene Einträge → `InvalidSbomError`.
- `serial_number`: `serialNumber`; länger als 100 Zeichen → `None`.
- `suggested_label`: `metadata.component.version`, sonst `metadata.timestamp`, sonst `None`.
- Keine Duplikat-Zusammenführung hier (macht Task 4).

- [ ] **Step 1: Failing tests** (kleine Dicts direkt im Test, je Fall eine Funktion):
  - `test_parses_npm_scoped_package`: purl `pkg:npm/%40tanstack/react-query@5.0.0` → `SbomEntry(name="@tanstack/react-query", version="5.0.0", ecosystem=Ecosystem.NPM, category=Category.LIBRARY, ...)`.
  - `test_parses_pypi_and_maven`: `pkg:pypi/fastapi@0.115.0` → `("fastapi", Ecosystem.PYPI)`; `pkg:maven/org.apache.logging.log4j/log4j-core@2.14.1` → `name == "org.apache.logging.log4j:log4j-core"`.
  - `test_os_package_is_unchecked`: `pkg:deb/debian/openssl@3.0.11-1` → `ecosystem is None`, `checked is False`, `name == "openssl"`.
  - `test_reads_nested_components_and_ignores_other_types`: `operating-system`-Eintrag fehlt im Ergebnis, verschachtelte `library` ist drin.
  - `test_direct_from_dependency_graph`: Root `bom-ref="root"`, `dependencies=[{"ref":"root","dependsOn":["a"]}]` → `a.direct is True`, `b.direct is False`.
  - `test_all_direct_without_graph`.
  - `test_skips_components_without_version`: `skipped == 1`.
  - `test_suggested_label_prefers_root_version`: `"1.4.0"`; ohne Root-Version → `metadata.timestamp`.
  - `test_rejects_wrong_format`: `{"spdxVersion": "SPDX-2.3"}` → `InvalidSbomError`; `specVersion "1.2"` → `InvalidSbomError`.
  - `test_rejects_too_many_components`: 50 001 Einträge → `InvalidSbomError`.
  - `test_purl_type_mapping_roundtrip`: für jedes Ökosystem in `PURL_ECOSYSTEMS` ist `ecosystem_for_purl_type(<typ>)` wieder das Ökosystem; `ecosystem_for_purl_type("deb") is None`.
- [ ] **Step 2:** `uv run pytest tests/unit/test_cyclonedx_parser.py -q` → FAIL.
- [ ] **Step 3:** Parser in kleinen Funktionen (`_validate_header`, `_walk_components`, `_entry_from`, `_direct_refs`, `_name_from_purl`) – je Komplexität ≤ 8. purl selbst parsen (`urllib.parse.unquote`, Qualifier `?…` und Subpath `#…` abschneiden), keine Library.
- [ ] **Step 4:** Tests → PASS, `uv run ruff check . && uv run mypy`.
- [ ] **Step 5: Commit** `feat: parse CycloneDX SBOMs`

### Task 4: Use Case „SBOM-Version hochladen“ mit Abgleich

**Files:**
- Create: `backend/app/application/sbom_reconcile.py`, `backend/app/application/sbom_use_cases.py`
- Test: `backend/tests/unit/test_sbom_reconcile.py`, `backend/tests/unit/test_sbom_use_cases.py`

**Interfaces:**
- Consumes: Task 1 (Modelle, Ports, Fehler), `normalize_package_name` aus `app/application/component_matching.py`.
- Produces:
  ```python
  # sbom_reconcile.py
  ComponentKey = tuple[str | None, str, str]
  def entry_key(entry: SbomEntry) -> ComponentKey
  def component_key(component: Component) -> ComponentKey
  def merge_duplicates(entries: Sequence[SbomEntry]) -> tuple[SbomEntry, ...]   # Reihenfolge des ersten Auftretens, direct = any
  @dataclass(frozen=True)
  class Reconciliation:
      to_add: tuple[SbomEntry, ...]
      to_keep: tuple[tuple[Component, SbomEntry], ...]
      to_remove: tuple[Component, ...]
  def reconcile(live: Sequence[Component], entries: Sequence[SbomEntry]) -> Reconciliation

  # sbom_use_cases.py
  @dataclass(frozen=True)
  class SbomUploadResult:
      sbom: Sbom; version: SbomVersion
      added: int; removed: int; kept: int; unchecked: int; skipped: int
  class UploadSbomVersion:
      def __init__(self, uow: UnitOfWork, parser: SbomParser, clock: Callable[[], datetime]) -> None
      def execute(self, *, application_id: int, name: str, label: str | None,
                  document: Mapping[str, object]) -> SbomUploadResult
  ```
  Ablauf wie im Spec (Abschnitt „Abgleich“). Label: `label.strip()` falls nicht leer, sonst `parsed.suggested_label`, sonst `clock()` als `"%Y-%m-%d %H:%M"`; auf 100 Zeichen kürzen. Name wird `strip()`-t; leer oder > 100 → `InvalidValueError`. Behaltene Komponenten: `components.update(replace(component, category=…, direct=…, checked=entry.checked))`. Entfernte: erst `findings.delete_for_component`, dann `components.delete`. Neue: `components.add(application_id, Component(..., sbom_id=sbom.id, checked=entry.checked))`. `unchecked` = Anzahl Einträge mit `checked False` nach Zusammenführung. Genau ein `uow.commit()`.

- [ ] **Step 1: Failing tests**
  - `test_merge_duplicates_keeps_one_and_any_direct` (Review Focus 1): zwei gleiche npm-Einträge, einer direkt → ein Eintrag, `direct is True`.
  - `test_reconcile_treats_pypi_spelling_as_same` (Review Focus 2): live `Jinja2 3.1.4`, neu `jinja2 3.1.4` → `to_keep` 1, `to_add`/`to_remove` leer.
  - `test_reconcile_version_change_is_remove_and_add`: `react 18.2.0` → `react 18.3.1`.
  - `test_first_upload_creates_sbom_version_and_components`: Ergebnis `added == 2`, `version.is_current`, Komponenten haben `sbom_id == sbom.id`, `uow.commits == 1`.
  - `test_second_upload_archives_previous_version`: `list_for_sbom` hat 2 Versionen, nur die neue `is_current`.
  - `test_kept_component_keeps_finding_status`: Treffer mit `FindingStatus` ≠ Standard und Kommentar an `react 18.2.0`; zweiter Upload mit `react 18.2.0` → Treffer unverändert vorhanden.
  - `test_removed_component_drops_findings`: zweiter Upload ohne `react` → Komponente und Treffer weg, `removed == 1`.
  - `test_manual_components_untouched`: manuelle Komponente `react 18.2.0` bleibt bei Upload und bei Entfernen gleichnamiger SBOM-Komponente.
  - `test_same_serial_as_current_is_rejected` (Review Focus 5): → `DuplicateSbomVersionError`, `uow.commits == 0`, weiterhin 1 Version.
  - `test_unknown_application_raises_not_found` (Review Focus 3).
  - `test_label_falls_back_to_suggestion_then_clock`.
  - Für die Tests einen `FakeSbomParser` in `tests/fakes.py` ergänzen, der ein vorgegebenes `ParsedSbom` zurückgibt.
- [ ] **Step 2:** `uv run pytest tests/unit/test_sbom_reconcile.py tests/unit/test_sbom_use_cases.py -q` → FAIL.
- [ ] **Step 3:** Umsetzen; `execute` in private Schritte aufteilen (`_resolve_sbom`, `_store_version`, `_apply`).
- [ ] **Step 4:** Tests → PASS, `uv run ruff check .`.
- [ ] **Step 5: Commit** `feat: upload SBOM versions and reconcile components`

### Task 5: Weitere Use Cases, Schutz manueller Bearbeitung, Ingest-Filter

**Files:**
- Modify: `backend/app/application/sbom_use_cases.py`, `backend/app/application/inventory_use_cases.py` (`UpdateComponent`), `backend/app/application/ingest.py:211-216`
- Test: `backend/tests/unit/test_sbom_use_cases.py`, `backend/tests/unit/test_inventory_use_cases.py`, `backend/tests/unit/test_ingest.py`

**Interfaces:**
- Produces (`sbom_use_cases.py`):
  ```python
  @dataclass(frozen=True)
  class SbomOverview:
      sbom: Sbom; current: SbomVersion | None; version_count: int
  class ListSboms:         execute(self, application_id: int) -> list[SbomOverview]   # nach Name sortiert
  class ListSbomVersions:  execute(self, *, application_id: int, sbom_id: int) -> list[SbomVersion]
  class GetSbomVersion:    execute(self, *, application_id: int, sbom_id: int, version_id: int) -> SbomVersion
  class DeleteSbom:        execute(self, *, application_id: int, sbom_id: int) -> None
  ```
  Alle prüfen Zugehörigkeit (Anwendung existiert, `sbom.application_id == application_id`, `version.sbom_id == sbom_id`), sonst `EntityNotFoundError`. `DeleteSbom` löscht Treffer + Live-Komponenten (`list_for_sbom`) und dann `sboms.delete`, ein Commit.
- `UpdateComponent` wirft `ComponentManagedBySbomError`, wenn `existing.sbom_id is not None`.
- Ingest berücksichtigt nur `component.checked`.

- [ ] **Step 1: Failing tests**
  - `test_list_sboms_returns_current_version_and_count`.
  - `test_sbom_of_other_application_is_not_found` (Review Focus 3): `ListSbomVersions`, `GetSbomVersion`, `DeleteSbom` mit fremder `application_id` → `EntityNotFoundError`.
  - `test_get_archived_version_returns_entries`.
  - `test_delete_sbom_removes_components_findings_versions`; manuelle Komponenten bleiben.
  - `test_update_sbom_component_is_rejected` → `ComponentManagedBySbomError`.
  - `test_ingest_skips_unchecked_components`: `FakePackageSource` bekommt nur Aufrufe für geprüfte Komponenten (`source.calls`).
- [ ] **Step 2:** Tests → FAIL.
- [ ] **Step 3:** Umsetzen.
- [ ] **Step 4:** `uv run pytest -q` → PASS.
- [ ] **Step 5: Commit** `feat: list, inspect and delete SBOMs`

### Task 6: API, Fehler-Mapping, Verdrahtung, nginx

**Files:**
- Create: `backend/app/presentation/sbom_router.py`
- Modify: `backend/app/presentation/error_handlers.py` (`ConflictError → 409`), `backend/app/presentation/app_factory.py` (`AppServices.sbom_parser: SbomParser | None`, `AppServices.clock: Callable[[], datetime] | None`, Router einbinden), `backend/app/presentation/inventory_router.py` (`ComponentResponse.sbom_id`, `.checked`), `backend/app/main.py` (`CycloneDxParser()`, `_now`), `frontend/nginx.conf`
- Test: `backend/tests/api/test_sbom_api.py`, `backend/tests/api/test_app.py` (bestehende Komponententests um neue Felder)

**Interfaces:**
- Consumes: Use Cases aus Task 4/5.
- Endpunkte (Pfade und Status exakt):
  - `GET /api/applications/{application_id}/sboms` → `list[SbomSummaryResponse]` mit `id`, `name`, `versionCount`, `current: SbomVersionSummaryResponse | None`.
  - `POST /api/applications/{application_id}/sboms/versions` Body `UploadSbomRequest{ name: str (1..100), label: str | None (≤100), document: dict[str, object] }` → 201 `SbomUploadResponse{ sbomId, version: SbomVersionSummaryResponse, added, removed, kept, unchecked, skipped }`.
  - `GET /api/applications/{application_id}/sboms/{sbom_id}/versions` → `list[SbomVersionSummaryResponse]`.
  - `GET /api/applications/{application_id}/sboms/{sbom_id}/versions/{version_id}` → `SbomVersionDetailResponse` (= Summary + `components: list[SbomEntryResponse]`).
  - `DELETE /api/applications/{application_id}/sboms/{sbom_id}` → 204.
  - `SbomVersionSummaryResponse{ id, label, uploadedAt, isCurrent, componentCount, uncheckedCount }`; `SbomEntryResponse{ name, version, category, ecosystem, direct, purl, checked }`.
  - `ComponentResponse` + `sbomId: int | None`, `checked: bool`. (Abweichung vom Spec: kein `sbomName`; das Frontend löst den Namen über die SBOM-Liste auf, damit der Router ohne Logik bleibt.)
- Parser und Uhr per Dependency aus `app.state` (Muster `get_ingest_runner` in `ingest_router.py`).
- nginx: zusätzlicher Block vor `location /api/`:
  ```nginx
  location ~ ^/api/applications/[0-9]+/sboms/versions$ {
      client_max_body_size 25m;
      # gleiche proxy_*-Zeilen wie /api/
  }
  ```
  `client_max_body_size` ist kein `add_header` → die Sicherheits-Header werden weiter vererbt; nur prüfen, dass im Block kein `add_header` steht.

- [ ] **Step 1: Failing API-Tests** (App mit `InMemoryUnitOfWork` und echtem `CycloneDxParser`, Muster `tests/api/test_cve_radar_api.py`):
  - `test_upload_sbom_returns_summary`: 201, `added == 2`, `version.isCurrent is True`.
  - `test_upload_same_serial_twice_returns_409` (Review Focus 5).
  - `test_upload_invalid_document_returns_422`: `document={"spdxVersion": "SPDX-2.3"}`.
  - `test_upload_for_unknown_application_returns_404` (Review Focus 3).
  - `test_list_versions_and_get_archived_version`.
  - `test_delete_sbom_returns_204_and_removes_components`: danach `GET /api/applications/{id}` ohne SBOM-Komponenten.
  - `test_update_sbom_component_returns_409`.
  - `test_component_response_has_sbom_id_and_checked`.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Umsetzen.
- [ ] **Step 4:** `make check` grün (inkl. `check-docker`); nginx-Syntax: `docker run --rm -v $PWD/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro <frontend-Basisimage aus frontend/Dockerfile> nginx -t` → `syntax is ok` (Upstream `backend` ggf. per `--add-host backend:127.0.0.1`).
- [ ] **Step 5: Commit** `feat: expose SBOM endpoints`

### Task 7: Frontend – Modell, Datei-Einlesen, API, Hooks

**Files:**
- Create: `frontend/src/features/inventory/model/sbom-types.ts`, `model/sbom-file.ts`, `model/sbom-schema.ts`, `api/sbom-api.ts`, `hooks/use-sboms.ts`, `hooks/use-sbom-versions.ts`, `hooks/use-sbom-version.ts`, `hooks/use-upload-sbom.ts`, `hooks/use-delete-sbom.ts`
- Modify: `frontend/src/features/inventory/model/types.ts` (`Component.sbomId: number | null`, `Component.checked: boolean`) und bestehende Test-Fixtures mit `Component`
- Test: `model/sbom-file.test.ts`, `api/sbom-api.test.ts`

**Interfaces:**
- Typen spiegeln Task 6 (camelCase): `SbomSummary`, `SbomVersionSummary`, `SbomVersionDetail`, `SbomEntry`, `SbomUploadResult`, `SbomUploadBody { name: string; label: string | null; document: Record<string, unknown> }`.
- `readSbomFile(file: File): Promise<SbomFile>` mit `SbomFile { document: Record<string, unknown>; suggestedName: string; suggestedLabel: string }`; `suggestedName` = `metadata.component.name` oder Dateiname ohne `.cdx.json`/`.json`; `suggestedLabel` = `metadata.component.version` oder `""`. Wirft `SbomFileError` mit `"Die Datei ist kein gültiges JSON."` bzw. `"Die Datei ist keine CycloneDX-SBOM."` (wenn `bomFormat !== "CycloneDX"`).
- `sbomUploadSchema` (zod): `name` 1–100 (`"Name ist erforderlich"`), `label` ≤ 100.
- API: `listSboms(applicationId)`, `uploadSbomVersion(applicationId, body)`, `listSbomVersions(applicationId, sbomId)`, `getSbomVersion(applicationId, sbomId, versionId)`, `deleteSbom(applicationId, sbomId)`.
- Query-Keys: `["sboms", applicationId]`, `["sbom-versions", applicationId, sbomId]`, `["sbom-version", applicationId, sbomId, versionId]`. Upload/Löschen invalidieren `["sboms", applicationId]`, `["sbom-versions", applicationId]`, `["application", applicationId]`, `["application-findings", applicationId]`, `["findings"]`.

- [ ] **Step 1: Failing tests**
  - `readSbomFile` liest Name und Version aus `metadata.component`.
  - Fallback auf Dateinamen `backend-image.cdx.json` → `"backend-image"`.
  - `"kein json"` → `SbomFileError("Die Datei ist kein gültiges JSON.")` (Review Focus 4).
  - SPDX-JSON → `SbomFileError("Die Datei ist keine CycloneDX-SBOM.")` (Review Focus 4).
  - `uploadSbomVersion` sendet `POST /api/applications/1/sboms/versions` mit JSON-Body (fetch-Mock wie in `inventory-api.test.ts`).
- [ ] **Step 2:** `cd frontend && npx vitest run src/features/inventory/model src/features/inventory/api` → FAIL.
- [ ] **Step 3:** Umsetzen (`File.text()`, `JSON.parse`, Typprüfung ohne `any`).
- [ ] **Step 4:** Tests → PASS, `npx tsc -b`.
- [ ] **Step 5: Commit** `feat: add SBOM client model and hooks`

### Task 8: Frontend – Tab „SBOMs“

**Files:**
- Create: `frontend/src/features/inventory/application-sboms-page.tsx` (Container), `components/sbom-list.tsx`, `components/sbom-upload-dialog.tsx`, `components/sbom-version-history.tsx`, `components/sbom-version-components.tsx`, `components/sbom-delete-dialog.tsx`
- Modify: `components/detail-tabs.tsx` (Prop `sbomsPanel: ReactNode`, Tab `SBOMs`, `data-testid="inventory-tab-sboms"`), `application-detail-page.tsx`
- Add: `cd frontend && npx shadcn@latest add alert-dialog` (siehe Global Constraints)
- Test: je Komponente `*.test.tsx`, `application-sboms-page.test.tsx`

**Interfaces:**
- Consumes: Task 7.
- Reine Komponenten und Props:
  - `SbomList({ sboms, onUploadNew, onUploadVersion, onShowHistory, onDelete })` – Callbacks mit `SbomSummary`. Leer → Text „Noch keine SBOM hinterlegt.“
  - `SbomUploadDialog({ open, fixedName, isSubmitting, error, onSubmit, onOpenChange })` – `onSubmit(values: { file: SbomFile; name: string; label: string })`; Datei-Input liest per `readSbomFile` und belegt Name/Label vor; bei `fixedName` ist das Namensfeld gesperrt. Zeigt `SbomFileError` und Server-Fehler (`error`) in `FieldError`. RHF + zod (`sbomUploadSchema`).
  - `SbomVersionHistory({ versions, selectedVersionId, onSelect })` – Liste mit Badge „aktuell“/„archiviert“.
  - `SbomVersionComponents({ version })` – Tabelle Name, Version, Ökosystem, purl, Badge „nicht geprüft“.
  - `SbomDeleteDialog({ sbom, isDeleting, onConfirm, onCancel })` – Text nennt `current.componentCount`.
  - Container `ApplicationSbomsPage({ applicationId })` hält Dialog-Zustände, ruft Hooks, zeigt nach Upload die Zusammenfassung „{added} hinzugefügt · {removed} entfernt · {kept} unverändert · {unchecked} nicht geprüft“ plus „Neue Treffer erscheinen nach dem nächsten Abgleich.“
- Test-IDs: `inventory-btn-sbom-upload`, `inventory-list-sboms`, `inventory-item-sbom-${id}`, `inventory-btn-sbom-new-version-${id}`, `inventory-btn-sbom-history-${id}`, `inventory-btn-sbom-delete-${id}`, `inventory-dialog-sbom-upload`, `inventory-input-sbom-file`, `inventory-input-sbom-name`, `inventory-input-sbom-label`, `inventory-btn-sbom-submit`, `inventory-error-sbom-upload`, `inventory-text-sbom-result`, `inventory-dialog-sbom-history`, `inventory-item-sbom-version-${id}`, `inventory-list-sbom-components`, `inventory-dialog-sbom-delete`, `inventory-btn-sbom-delete-confirm`.

- [ ] **Step 1: Failing tests** (über `getByTestId`):
  - Liste zeigt Name, aktuelle Bezeichnung und „318 nicht geprüft“.
  - Upload-Dialog: Datei wählen belegt Name/Label vor; Absenden ruft `onSubmit` mit Datei, Name, Label.
  - Upload-Dialog: ungültige Datei zeigt `inventory-error-sbom-upload` mit Meldung, `onSubmit` wird nicht gerufen (Review Focus 4).
  - „Neue Version“: Namensfeld gesperrt mit `fixedName`.
  - Verlauf: Klick auf archivierte Version ruft `onSelect(id)`; Badge „archiviert“.
  - Löschen-Dialog nennt Komponentenzahl, Bestätigen ruft `onConfirm`.
  - Container (Hooks gemockt wie in `application-cves-page.test.tsx`): nach erfolgreichem Upload steht die Zusammenfassung in `inventory-text-sbom-result`.
- [ ] **Step 2:** `npx vitest run src/features/inventory` → FAIL.
- [ ] **Step 3:** Umsetzen mit vorhandenen shadcn-Komponenten (`dialog`, `table`, `badge`, `field`, `input`, `button`, neu `alert-dialog`); vorher `npx shadcn@latest search` prüfen.
- [ ] **Step 4:** `make check-frontend` grün.
- [ ] **Step 5: Commit** `feat: manage SBOMs in application detail`

### Task 9: Frontend – Spalte „Quelle“ im Komponenten-Tab

**Files:**
- Modify: `components/component-table.tsx`, `components/components-tab.tsx`, `components/detail-tabs.tsx`, `application-detail-page.tsx`
- Test: `components/component-table.test.tsx`, `components/components-tab.test.tsx`

**Interfaces:**
- `ComponentTable` bekommt `sbomNames: ReadonlyMap<number, string>`; Spalte „Quelle“ zeigt `"manuell"` bei `sbomId === null`, sonst den Namen (fehlt → `"SBOM"`). Badge „nicht geprüft“ (`data-testid="inventory-text-unchecked-${id}"`) bei `checked === false`. Bearbeiten-Button nur bei `sbomId === null`.
- `application-detail-page.tsx` holt `useSboms(applicationId)` und baut die Map; `ComponentsTab`/`DetailTabs` reichen sie durch.

- [ ] **Step 1: Failing tests**
  - Manuelle Komponente zeigt „manuell“ und hat `inventory-btn-edit-10`.
  - SBOM-Komponente zeigt „backend-image“, hat kein `inventory-btn-edit-…`, zeigt Badge „nicht geprüft“ bei `checked: false`.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Umsetzen.
- [ ] **Step 4:** `make check` grün.
- [ ] **Step 5: Commit** `feat: show component source in inventory`

### Task 10: Abschluss

- [ ] **Step 1:** Ende-zu-Ende von Hand: `make dev-services`, `cd frontend && npm run dev`, eine von der Action erzeugte SBOM (oder lokal `trivy fs --format cyclonedx backend/`) hochladen, zweite Version hochladen, Verlauf und Archivliste ansehen, SBOM löschen (Skill `run`).
- [ ] **Step 2:** `docs/local-development.md` um einen kurzen Absatz „SBOM hochladen“ ergänzen; `make check` grün.
- [ ] **Step 3:** Subagent `fullstack-standards:architecture-reviewer` über den ganzen Branch, Funde beheben.
- [ ] **Step 4: Commit** `docs: describe SBOM upload`
