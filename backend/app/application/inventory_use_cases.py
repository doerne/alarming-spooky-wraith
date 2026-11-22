"""Use Cases zur manuellen Pflege des Inventars."""

from dataclasses import replace
from datetime import datetime

from app.application.ingest import Clock
from app.application.unit_of_work import UnitOfWork
from app.domain.errors import ComponentManagedBySbomError, EntityNotFoundError
from app.domain.inventory import Application, Component


def mark_inventory_changed(uow: UnitOfWork, application_id: int, now: datetime) -> None:
    """Merkt sich, dass sich das Inventar seit dem letzten Scan geändert hat."""
    application = uow.applications.get(application_id)
    uow.applications.update(application.mark_inventory_changed(now))


class CreateApplication:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self, *, name: str, description: str = "") -> Application:
        application = self._uow.applications.add(
            Application(name=name, description=description, inventory_changed_at=self._clock())
        )
        self._uow.commit()
        return application


class AddComponent:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self, *, application_id: int, component: Component) -> Component:
        self._uow.applications.get(application_id)  # EntityNotFoundError, falls unbekannt
        saved = self._uow.components.add(application_id, component)
        mark_inventory_changed(self._uow, application_id, self._clock())
        self._uow.commit()
        return saved


class ListApplications:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> list[Application]:
        return self._uow.applications.list()


class UpdateComponent:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self, *, application_id: int, component_id: int, component: Component) -> Component:
        self._uow.applications.get(application_id)  # EntityNotFoundError, falls unbekannt
        existing = self._uow.components.get(component_id)
        if existing.application_id != application_id:
            raise EntityNotFoundError("Komponente", component_id)
        if existing.sbom_id is not None:
            raise ComponentManagedBySbomError(component_id)
        updated = self._uow.components.update(
            replace(component, id=component_id, application_id=application_id)
        )
        mark_inventory_changed(self._uow, application_id, self._clock())
        self._uow.commit()
        return updated


class GetApplication:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, application_id: int) -> Application:
        application = self._uow.applications.get(application_id)  # EntityNotFoundError
        application.components = [
            component
            for component in self._uow.components.list_for_application(application_id)
            if not component.is_retired
        ]
        return application
