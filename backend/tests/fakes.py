"""In-Memory-Adapter für schnelle Tests ohne Datenbank."""

from dataclasses import replace

from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Component
from app.domain.ports import SourceReference, SourceVuln
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
            finding.id = self._items[key].id
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


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0
        self.applications = InMemoryApplicationRepository()
        self.components = InMemoryComponentRepository()
        self.findings = InMemoryFindingRepository()
        self.advisories = InMemoryAdvisoryRepository()

    def commit(self) -> None:
        self.commits += 1


class FakeOsvClient:
    def __init__(self, vulns_by_name: dict[str, list[SourceVuln]]) -> None:
        self._vulns_by_name = vulns_by_name

    def query(self, ecosystem: str, name: str, version: str) -> list[SourceVuln]:
        return self._vulns_by_name.get(name, [])


class FakeAdvisoryStore:
    def __init__(self) -> None:
        self.saved: dict[str, str] = {}

    def save(
        self, advisory: Advisory, *, tags: list[str], sources: list[SourceReference], body: str
    ) -> str:
        self.saved[advisory.advisory_id] = body
        return f"advisories/{advisory.advisory_id}.md"

    def read(self, advisory_id: str) -> str:
        return self.saved[advisory_id]
