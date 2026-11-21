from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Protocol

from app.domain.ports import (
    AdvisoryAliasRepository,
    AdvisoryRepository,
    ApplicationRepository,
    ComponentRepository,
    FindingRepository,
    SbomRepository,
    SbomVersionRepository,
    SourceSettingRepository,
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
    @property
    def advisory_aliases(self) -> AdvisoryAliasRepository: ...
    @property
    def source_settings(self) -> SourceSettingRepository: ...
    @property
    def sboms(self) -> SbomRepository: ...
    @property
    def sbom_versions(self) -> SbomVersionRepository: ...
    def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], AbstractContextManager[UnitOfWork]]
