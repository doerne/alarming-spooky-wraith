from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Protocol

from app.domain.ports import (
    AdvisoryRepository,
    ApplicationRepository,
    ComponentRepository,
    FindingRepository,
)


class UnitOfWork(Protocol):
    """Transaktionsgrenze. Use Cases entscheiden, wann bestätigt wird."""

    @property
    def applications(self) -> ApplicationRepository: ...
    @property
    def components(self) -> ComponentRepository: ...
    @property
    def findings(self) -> FindingRepository: ...
    @property
    def advisories(self) -> AdvisoryRepository: ...
    def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], AbstractContextManager[UnitOfWork]]
