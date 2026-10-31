from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

from app.domain.ports import (
    AdvisoryRepository,
    ApplicationRepository,
    ComponentRepository,
    FindingRepository,
)


class SqlAlchemyUnitOfWork:
    """Haelt die Repositories fuer eine Session.

    Die konkreten Repository-Implementierungen werden in Task 8 angelegt und
    hier verdrahtet; bis dahin erfuellen die Properties nur das Protocol.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def applications(self) -> ApplicationRepository:
        raise NotImplementedError

    @property
    def components(self) -> ComponentRepository:
        raise NotImplementedError

    @property
    def findings(self) -> FindingRepository:
        raise NotImplementedError

    @property
    def advisories(self) -> AdvisoryRepository:
        raise NotImplementedError

    def commit(self) -> None:
        self._session.commit()


@contextmanager
def sqlalchemy_unit_of_work(
    session_factory: sessionmaker[Session],
) -> Iterator[SqlAlchemyUnitOfWork]:
    """Öffnet eine Session pro Anfrage. Nicht bestätigte Änderungen werden verworfen."""
    with session_factory() as session:
        yield SqlAlchemyUnitOfWork(session)
