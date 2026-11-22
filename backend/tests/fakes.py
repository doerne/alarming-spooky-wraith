"""In-Memory-Adapter für schnelle Tests ohne Datenbank."""

import builtins
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime

from app.application.github_sync import SyncRequest, SyncRunState
from app.application.ingest_runner import IngestRunState
from app.application.issue_export import IssueDraft
from app.domain.errors import EntityNotFoundError, IssueTrackerError
from app.domain.inventory import Application, Component
from app.domain.ports import (
    AdvisoryDocument,
    IssueContent,
    SourceReference,
    SourceVuln,
    TrackedIssue,
)
from app.domain.sbom import ParsedSbom, Sbom, SbomVersion
from app.domain.scan_run import ScanRun, ScanTrigger
from app.domain.sources import (
    ApiKeyRequirement,
    MatchScope,
    SourceDescriptor,
    SourceKind,
    SourceSetting,
)
from app.domain.vulnerability import (
    Advisory,
    Finding,
    FindingResolution,
    FindingStatus,
    IssueState,
)


class InMemoryApplicationRepository:
    def __init__(self) -> None:
        self._items: dict[int, Application] = {}
        self._next_id = 1

    def add(self, application: Application) -> Application:
        application.id = self._next_id
        self._items[self._next_id] = application
        self._next_id += 1
        return application

    def get(self, application_id: int) -> Application:
        if application_id not in self._items:
            raise EntityNotFoundError("Anwendung", application_id)
        return self._items[application_id]

    def list(self) -> list[Application]:
        return list(self._items.values())

    def update(self, application: Application) -> Application:
        assert application.id is not None
        if application.id not in self._items:
            raise EntityNotFoundError("Anwendung", application.id)
        self._items[application.id] = application
        return application


class InMemoryComponentRepository:
    def __init__(self) -> None:
        self._items: list[tuple[int, Component]] = []
        self._next_id = 1

    def add(self, application_id: int, component: Component) -> Component:
        saved = replace(component, id=self._next_id, application_id=application_id)
        self._items.append((application_id, saved))
        self._next_id += 1
        return saved

    def get(self, component_id: int) -> Component:
        for _, component in self._items:
            if component.id == component_id:
                return component
        raise EntityNotFoundError("Komponente", component_id)

    def update(self, component: Component) -> Component:
        assert component.id is not None
        for index, (app_id, existing) in enumerate(self._items):
            if existing.id == component.id:
                self._items[index] = (app_id, component)
                return component
        raise EntityNotFoundError("Komponente", component.id)

    def list_all(self) -> list[Component]:
        return [component for _, component in self._items]

    def list_for_application(self, application_id: int) -> list[Component]:
        return [component for app_id, component in self._items if app_id == application_id]

    def list_for_sbom(self, sbom_id: int) -> list[Component]:
        return [component for _, component in self._items if component.sbom_id == sbom_id]

    def add_many(self, application_id: int, components: Sequence[Component]) -> None:
        for component in components:
            self.add(application_id, component)

    def delete_many(self, component_ids: Sequence[int]) -> None:
        doomed = set(component_ids)
        self._items = [item for item in self._items if item[1].id not in doomed]

    def retire_many(self, component_ids: Sequence[int], version_id: int) -> None:
        retired = set(component_ids)
        self._items = [
            (
                application_id,
                replace(component, retired_in_version_id=version_id)
                if component.id in retired
                else component,
            )
            for application_id, component in self._items
        ]

    def application_id_of(self, component_id: int) -> int:
        for application_id, component in self._items:
            if component.id == component_id:
                return application_id
        raise EntityNotFoundError("Komponente", component_id)


class InMemoryFindingRepository:
    def __init__(self) -> None:
        self._items: dict[tuple[str, int], Finding] = {}
        self._next_id = 1

    def upsert(self, finding: Finding) -> Finding:
        key = (finding.advisory_id, finding.component_id)
        if key in self._items:
            existing = self._items[key]
            finding.id = existing.id
            finding.status = existing.status
            finding.comment = existing.comment
            finding.resolved_at = existing.resolved_at
            finding.resolution = existing.resolution
            finding.resolved_by = existing.resolved_by
            finding.issue_url = existing.issue_url
            finding.issue_state = existing.issue_state
            finding.first_seen_at = existing.first_seen_at
        else:
            finding.id = self._next_id
            self._next_id += 1
            finding.first_seen_at = finding.first_seen_at or datetime.now(UTC)
        self._items[key] = finding
        return finding

    def list(self) -> list[Finding]:
        return list(self._items.values())

    def _key_of(self, finding_id: int) -> tuple[str, int]:
        for key, finding in self._items.items():
            if finding.id == finding_id:
                return key
        raise EntityNotFoundError("Fund", finding_id)

    def list_for_components(self, component_ids: Sequence[int]) -> builtins.list[Finding]:
        wanted = set(component_ids)
        return [finding for finding in self._items.values() if finding.component_id in wanted]

    def components_with_findings(self, component_ids: Sequence[int]) -> set[int]:
        wanted = set(component_ids)
        return {
            finding.component_id
            for finding in self._items.values()
            if finding.component_id in wanted
        }

    def list_for_advisory(self, advisory_id: str) -> builtins.list[Finding]:
        return [finding for finding in self._items.values() if finding.advisory_id == advisory_id]

    def reassign(self, finding_id: int, advisory_id: str) -> None:
        finding = self._items.pop(self._key_of(finding_id))
        finding.advisory_id = advisory_id
        self._items[(advisory_id, finding.component_id)] = finding

    def save_triage(self, finding_id: int, status: FindingStatus, comment: str) -> None:
        finding = self._items[self._key_of(finding_id)]
        finding.status = status
        finding.comment = comment

    def resolve(self, finding_id: int, resolution: FindingResolution) -> None:
        finding = self._items[self._key_of(finding_id)]
        finding.status = resolution.status
        finding.resolved_at = resolution.resolved_at
        finding.resolution = resolution.text
        finding.resolved_by = resolution.source

    def save_report(self, finding: Finding) -> None:
        assert finding.id is not None
        self._items[self._key_of(finding.id)] = replace(finding)

    def save_issue_link(
        self, finding_id: int, issue_url: str, issue_state: IssueState | None
    ) -> None:
        finding = self._items[self._key_of(finding_id)]
        finding.issue_url = issue_url
        finding.issue_state = issue_state

    def delete(self, finding_id: int) -> None:
        del self._items[self._key_of(finding_id)]

    def delete_for_components(self, component_ids: Sequence[int]) -> None:
        doomed = set(component_ids)
        self._items = {
            key: finding
            for key, finding in self._items.items()
            if finding.component_id not in doomed
        }


class InMemorySbomVersionRepository:
    def __init__(self) -> None:
        self._items: dict[int, SbomVersion] = {}
        self._next_id = 1

    def add(self, version: SbomVersion) -> SbomVersion:
        saved = replace(version, id=self._next_id)
        self._items[self._next_id] = saved
        self._next_id += 1
        return saved

    def get(self, version_id: int) -> SbomVersion:
        if version_id not in self._items:
            raise EntityNotFoundError("SBOM-Version", version_id)
        return self._items[version_id]

    def current_for_sbom(self, sbom_id: int) -> SbomVersion | None:
        current = [v for v in self.list_for_sbom(sbom_id) if v.is_current]
        return current[0] if current else None

    def list_for_sbom(self, sbom_id: int) -> list[SbomVersion]:
        versions = [v for v in self._items.values() if v.sbom_id == sbom_id]
        return sorted(versions, key=lambda version: version.id or 0, reverse=True)

    def archive(self, version_id: int) -> None:
        self._items[version_id] = replace(self.get(version_id), is_current=False)

    def delete_for_sbom(self, sbom_id: int) -> None:
        self._items = {key: v for key, v in self._items.items() if v.sbom_id != sbom_id}


class InMemorySbomRepository:
    def __init__(self, versions: InMemorySbomVersionRepository) -> None:
        self._items: dict[int, Sbom] = {}
        self._next_id = 1
        self._versions = versions

    def add(self, sbom: Sbom) -> Sbom:
        sbom.id = self._next_id
        self._items[self._next_id] = sbom
        self._next_id += 1
        return sbom

    def get(self, sbom_id: int) -> Sbom:
        if sbom_id not in self._items:
            raise EntityNotFoundError("SBOM", sbom_id)
        return self._items[sbom_id]

    def find_by_name(self, application_id: int, name: str) -> Sbom | None:
        for sbom in self._items.values():
            if sbom.application_id == application_id and sbom.name == name:
                return sbom
        return None

    def list_for_application(self, application_id: int) -> list[Sbom]:
        return [sbom for sbom in self._items.values() if sbom.application_id == application_id]

    def delete(self, sbom_id: int) -> None:
        self._items.pop(sbom_id, None)
        self._versions.delete_for_sbom(sbom_id)


class FakeSbomParser:
    """Liefert ein vorgegebenes Ergebnis; merkt sich das übergebene Dokument."""

    def __init__(self, parsed: ParsedSbom) -> None:
        self.parsed = parsed
        self.documents: list[Mapping[str, object]] = []

    def parse(self, document: Mapping[str, object]) -> ParsedSbom:
        self.documents.append(document)
        return self.parsed


class InMemoryAdvisoryRepository:
    def __init__(self) -> None:
        self._items: dict[str, Advisory] = {}

    def upsert(self, advisory: Advisory) -> Advisory:
        self._items[advisory.advisory_id] = advisory
        return advisory

    def get(self, advisory_id: str) -> Advisory:
        if advisory_id not in self._items:
            raise EntityNotFoundError("Advisory", advisory_id)
        return self._items[advisory_id]

    def find(self, advisory_id: str) -> Advisory | None:
        return self._items.get(advisory_id)

    def delete(self, advisory_id: str) -> None:
        self._items.pop(advisory_id, None)


class InMemoryAdvisoryAliasRepository:
    def __init__(self) -> None:
        self._items: dict[str, str] = {}

    def save(self, alias_id: str, advisory_id: str) -> None:
        self._items[alias_id] = advisory_id

    def remove(self, alias_id: str) -> None:
        self._items.pop(alias_id, None)

    def repoint(self, old_advisory_id: str, new_advisory_id: str) -> None:
        for alias_id, target in self._items.items():
            if target == old_advisory_id:
                self._items[alias_id] = new_advisory_id

    def resolve(self, alias_id: str) -> str | None:
        return self._items.get(alias_id)


class InMemorySourceSettingRepository:
    def __init__(self) -> None:
        self._items: dict[str, SourceSetting] = {}

    def get_all(self) -> list[SourceSetting]:
        return [replace(setting) for setting in self._items.values()]

    def get(self, source_key: str) -> SourceSetting | None:
        setting = self._items.get(source_key)
        return replace(setting) if setting else None

    def save(self, setting: SourceSetting) -> None:
        self._items[setting.source_key] = replace(setting)


class InMemoryScanRunRepository:
    def __init__(self) -> None:
        self._runs: dict[int, ScanRun] = {}

    def add(self, run: ScanRun) -> ScanRun:
        saved = replace(run, id=len(self._runs) + 1)
        self._runs[saved.id or 0] = saved
        return saved

    def update(self, run: ScanRun) -> ScanRun:
        if run.id not in self._runs:
            raise EntityNotFoundError("Scan-Lauf", str(run.id))
        self._runs[run.id] = run
        return run

    def list_unfinished(self) -> list[ScanRun]:
        return [run for run in self._runs.values() if run.finished_at is None]

    def latest_finished(self) -> ScanRun | None:
        return self._newest(run for run in self._runs.values() if run.finished_at)

    def latest_usable(self) -> ScanRun | None:
        return self._newest(run for run in self._runs.values() if run.usable)

    def latest_regular_finished(self) -> ScanRun | None:
        return self._newest(
            run for run in self._runs.values() if run.finished_at and not run.interrupted
        )

    def latest_started(self, trigger: ScanTrigger) -> ScanRun | None:
        return self._newest(run for run in self._runs.values() if run.trigger == trigger)

    @staticmethod
    def _newest(runs: Iterable[ScanRun]) -> ScanRun | None:
        return max(runs, key=lambda run: (run.started_at, run.id or 0), default=None)


class FakeIssueTracker:
    """Speicher-Tracker: Issues je Repo, Marker-Index, Aufzeichnung der Schreibzugriffe."""

    def __init__(self, *, configured: bool = True) -> None:
        self.configured = configured
        self.issues: dict[tuple[str, int], TrackedIssue] = {}
        self.markers: dict[str, dict[str, TrackedIssue]] = {}
        self.created: list[tuple[str, IssueContent]] = []
        self.set_open_calls: list[tuple[str, int, bool, str, bool]] = []
        self.failing_repos: set[str] = set()
        self._next_number = 1

    def is_configured(self) -> bool:
        return self.configured

    def existing_markers(self, repository: str) -> dict[str, TrackedIssue]:
        self._guard(repository)
        return dict(self.markers.get(repository, {}))

    def get(self, repository: str, number: int) -> TrackedIssue | None:
        self._guard(repository)
        return self.issues.get((repository, number))

    def create(self, repository: str, content: IssueContent) -> TrackedIssue:
        self._guard(repository)
        issue = self._track(repository, self._next_number, is_open=True)
        self._next_number += 1
        self.markers.setdefault(repository, {})[content.marker] = issue
        self.created.append((repository, content))
        return issue

    def set_open(
        self, repository: str, number: int, is_open: bool, comment: str, not_planned: bool = False
    ) -> None:
        self._guard(repository)
        self.set_open_calls.append((repository, number, is_open, comment, not_planned))
        self._track(repository, number, is_open=is_open, not_planned=not_planned)

    def add_issue(
        self, repository: str, number: int, *, is_open: bool, not_planned: bool = False
    ) -> None:
        self._track(repository, number, is_open=is_open, not_planned=not_planned)

    def _track(
        self, repository: str, number: int, *, is_open: bool, not_planned: bool = False
    ) -> TrackedIssue:
        issue = TrackedIssue(
            number=number,
            url=f"https://github.com/{repository}/issues/{number}",
            is_open=is_open,
            not_planned=not_planned,
        )
        self.issues[(repository, number)] = issue
        return issue

    def _guard(self, repository: str) -> None:
        if repository in self.failing_repos:
            raise IssueTrackerError("GitHub ist nicht erreichbar")


class FakeIssueFormatter:
    def format(self, application_id: int, draft: IssueDraft) -> IssueContent:
        marker = f"<!-- cve-radar:application={application_id};advisory={draft.advisory_id} -->"
        return IssueContent(
            title=draft.title, body=f"Text {marker}", labels=("security",), marker=marker
        )


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.applications = InMemoryApplicationRepository()
        self.components = InMemoryComponentRepository()
        self.findings = InMemoryFindingRepository()
        self.advisories = InMemoryAdvisoryRepository()
        self.advisory_aliases = InMemoryAdvisoryAliasRepository()
        self.source_settings = InMemorySourceSettingRepository()
        self.sbom_versions = InMemorySbomVersionRepository()
        self.sboms = InMemorySbomRepository(self.sbom_versions)
        self.scan_runs = InMemoryScanRunRepository()

    def rollback(self) -> None:
        self.rollbacks += 1

    def commit(self) -> None:
        self.commits += 1


class FakeAdvisoryStore:
    def __init__(self, reject: set[str] | None = None) -> None:
        self.saved: dict[str, str] = {}
        self.documents: dict[str, AdvisoryDocument] = {}
        self._reject = reject or set()

    def save(
        self, advisory: Advisory, *, tags: list[str], sources: list[SourceReference], body: str
    ) -> str:
        if advisory.advisory_id in self._reject:
            raise ValueError(f"Unzulaessige Advisory-ID: {advisory.advisory_id!r}")
        self.saved[advisory.advisory_id] = body
        self.documents[advisory.advisory_id] = AdvisoryDocument(body, "", [], list(sources))
        return f"advisories/{advisory.advisory_id}.md"

    def read(self, advisory_id: str) -> str:
        return self.saved[advisory_id]

    def read_document(self, advisory_id: str) -> AdvisoryDocument | None:
        return self.documents.get(advisory_id)

    def delete(self, advisory_id: str) -> None:
        self.saved.pop(advisory_id, None)
        self.documents.pop(advisory_id, None)


class FakePackageSource:
    """Paket-Quelle für Tests; merkt sich jeden Aufruf (Name, API-Key)."""

    def __init__(
        self,
        descriptor: SourceDescriptor,
        vulns_by_name: dict[str, list[SourceVuln]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.descriptor = descriptor
        self._vulns_by_name = vulns_by_name or {}
        self._error = error
        self.calls: list[tuple[str, str | None]] = []

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:
        self.calls.append((component.name, api_key))
        if self._error is not None:
            raise self._error
        return self._vulns_by_name.get(component.name, [])


class FakeBulkSource:
    """Gesamtabzug-Quelle für Tests."""

    def __init__(
        self,
        descriptor: SourceDescriptor,
        vulns: list[SourceVuln] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.descriptor = descriptor
        self._vulns = vulns or []
        self._error = error
        self.loads = 0
        self.names: list[frozenset[str]] = []

    def load(self, api_key: str | None, names: frozenset[str]) -> list[SourceVuln]:
        self.loads += 1
        self.names.append(names)
        if self._error is not None:
            raise self._error
        return list(self._vulns)


def descriptor(
    key: str,
    *,
    kind: SourceKind = SourceKind.PACKAGE_QUERY,
    scope: MatchScope = MatchScope.PACKAGE,
    requirement: ApiKeyRequirement = ApiKeyRequirement.NONE,
    ecosystems: frozenset[str] = frozenset(),
) -> SourceDescriptor:
    return SourceDescriptor(
        key=key,
        name=key.upper(),
        homepage_url=f"https://{key}.example.org",
        description=f"Quelle {key}",
        kind=kind,
        scope=scope,
        api_key_requirement=requirement,
        api_key_hint="Format <a>:<b>" if requirement == ApiKeyRequirement.REQUIRED else "",
        ecosystems=ecosystems,
    )


VulnerabilitySourceFake = FakePackageSource | FakeBulkSource


class FakeIngestRunner:
    """Runner ohne Thread: merkt sich Starts und meldet einen festen Zustand."""

    def __init__(self, state: IngestRunState | None = None) -> None:
        self._state = state or IngestRunState(running=False)
        self.starts = 0
        self.triggers: list[ScanTrigger] = []

    def start(self, trigger: ScanTrigger = ScanTrigger.MANUAL) -> bool:
        if self._state.running:
            return False
        self.starts += 1
        self.triggers.append(trigger)
        self._state = IngestRunState(running=True, started_at=self._state.started_at)
        return True

    def state(self) -> IngestRunState:
        return self._state


class FakeSyncRunner:
    """Sync-Runner ohne Thread: merkt sich Aufträge, Sperre lässt sich vorgeben."""

    def __init__(self, *, busy: bool = False) -> None:
        self.busy = busy
        self.requests: list[SyncRequest] = []

    def start(self, request: SyncRequest) -> bool:
        if self.busy:
            return False
        self.requests.append(request)
        return True

    def state(self) -> SyncRunState:
        return SyncRunState(running=self.busy)
