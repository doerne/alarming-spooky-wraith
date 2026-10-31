"""Use Cases zur manuellen Pflege des Inventars."""

from app.application.unit_of_work import UnitOfWork
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
