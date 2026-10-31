"""Use Cases zur manuellen Pflege des Inventars."""

from dataclasses import replace

from app.application.unit_of_work import UnitOfWork
from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Component


class CreateApplication:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, *, name: str, description: str = "") -> Application:
        application = self._uow.applications.add(Application(name=name, description=description))
        self._uow.commit()
        return application


class AddComponent:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, *, application_id: int, component: Component) -> Component:
        self._uow.applications.get(application_id)  # EntityNotFoundError, falls unbekannt
        saved = self._uow.components.add(application_id, component)
        self._uow.commit()
        return saved


class ListApplications:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> list[Application]:
        return self._uow.applications.list()


class UpdateComponent:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, *, application_id: int, component_id: int, component: Component) -> Component:
        self._uow.applications.get(application_id)  # EntityNotFoundError, falls unbekannt
        existing = self._uow.components.get(component_id)
        if existing.application_id != application_id:
            raise EntityNotFoundError("Komponente", component_id)
        updated = self._uow.components.update(
            replace(component, id=component_id, application_id=application_id)
        )
        self._uow.commit()
        return updated


class GetApplication:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, application_id: int) -> Application:
        application = self._uow.applications.get(application_id)  # EntityNotFoundError
        application.components = self._uow.components.list_for_application(application_id)
        return application
