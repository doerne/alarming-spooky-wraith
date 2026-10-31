from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.repositories import (
    SqlAlchemyAdvisoryRepository,
    SqlAlchemyApplicationRepository,
    SqlAlchemyComponentRepository,
    SqlAlchemyFindingRepository,
)


class SqlAlchemyUnitOfWork:
    """Haelt die Repositories fuer eine Session."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.applications = SqlAlchemyApplicationRepository(session)
        self.components = SqlAlchemyComponentRepository(session)
        self.findings = SqlAlchemyFindingRepository(session)
        self.advisories = SqlAlchemyAdvisoryRepository(session)

    def commit(self) -> None:
        self._session.commit()


@contextmanager
def sqlalchemy_unit_of_work(
    session_factory: sessionmaker[Session],
) -> Iterator[SqlAlchemyUnitOfWork]:
    """Öffnet eine Session pro Anfrage. Nicht bestätigte Änderungen werden verworfen."""
    with session_factory() as session:
        yield SqlAlchemyUnitOfWork(session)
