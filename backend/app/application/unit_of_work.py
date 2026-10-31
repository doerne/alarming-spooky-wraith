from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Protocol


class UnitOfWork(Protocol):
    """Transaktionsgrenze. Use Cases entscheiden, wann bestätigt wird.

    Jedes neue Repository hier als read-only Property ergänzen, z. B.:

        @property
        def orders(self) -> OrderRepository: ...
    """

    def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], AbstractContextManager[UnitOfWork]]
