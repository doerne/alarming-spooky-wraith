"""Registry aller im Code eingebauten Quellen. Der Composition Root füllt sie."""

from collections.abc import Sequence

from app.domain.errors import EntityNotFoundError
from app.domain.ports import VulnerabilitySource
from app.domain.sources import SourceDescriptor


class SourceRegistry:
    def __init__(self, sources: Sequence[VulnerabilitySource]) -> None:
        self._sources: dict[str, VulnerabilitySource] = {}
        for source in sources:
            key = source.descriptor.key
            if key in self._sources:
                raise ValueError(f"Quelle {key} ist doppelt registriert")
            self._sources[key] = source

    def descriptors(self) -> list[SourceDescriptor]:
        return [source.descriptor for source in self._sources.values()]

    def get(self, key: str) -> VulnerabilitySource:
        if key not in self._sources:
            raise EntityNotFoundError("Quelle", key)
        return self._sources[key]

    def all(self) -> list[VulnerabilitySource]:
        return list(self._sources.values())
