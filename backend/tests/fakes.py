"""In-Memory-Adapter für schnelle Tests ohne Datenbank."""

from dataclasses import replace

from app.application.ingest_runner import IngestRunState
from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Component
from app.domain.ports import AdvisoryDocument, SourceReference, SourceVuln
from app.domain.sources import (
    ApiKeyRequirement,
    MatchScope,
    SourceDescriptor,
    SourceKind,
    SourceSetting,
)
from app.domain.vulnerability import Advisory, Finding


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
        else:
            finding.id = self._next_id
            self._next_id += 1
        self._items[key] = finding
        return finding

    def list(self) -> list[Finding]:
        return list(self._items.values())


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


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0
        self.applications = InMemoryApplicationRepository()
        self.components = InMemoryComponentRepository()
        self.findings = InMemoryFindingRepository()
        self.advisories = InMemoryAdvisoryRepository()
        self.source_settings = InMemorySourceSettingRepository()

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

    def start(self) -> bool:
        if self._state.running:
            return False
        self.starts += 1
        self._state = IngestRunState(running=True, started_at=self._state.started_at)
        return True

    def state(self) -> IngestRunState:
        return self._state
