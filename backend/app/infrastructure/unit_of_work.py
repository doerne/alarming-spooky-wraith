from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker


class SqlAlchemyUnitOfWork:
    """Neue Repositories im Konstruktor anlegen.

    Beispiel: self.orders = SqlAlchemyOrderRepository(session)
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()


@contextmanager
def sqlalchemy_unit_of_work(
    session_factory: sessionmaker[Session],
) -> Iterator[SqlAlchemyUnitOfWork]:
    """Öffnet eine Session pro Anfrage. Nicht bestätigte Änderungen werden verworfen."""
    with session_factory() as session:
        yield SqlAlchemyUnitOfWork(session)
