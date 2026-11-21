"""Liest CycloneDX-JSON-Dokumente in SBOM-Einträge ein."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from urllib.parse import unquote

from app.domain.errors import InvalidSbomError
from app.domain.inventory import (
    COMPONENT_NAME_MAX_LENGTH,
    COMPONENT_VERSION_MAX_LENGTH,
    Category,
    Ecosystem,
)
from app.domain.sbom import SBOM_MAX_COMPONENTS, SBOM_SERIAL_MAX_LENGTH, ParsedSbom, SbomEntry
from app.infrastructure.sources.purl import ecosystem_for_purl_type

SUPPORTED_SPEC_VERSIONS = ("1.4", "1.5", "1.6", "1.7")
_IMPORTED_TYPES = frozenset({"library", "framework", "application"})


@dataclass(frozen=True)
class _PackageId:
    ecosystem: Ecosystem | None
    name: str


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _validate_header(document: Mapping[str, object]) -> list[object]:
    if document.get("bomFormat") != "CycloneDX":
        raise InvalidSbomError("Die Datei ist keine CycloneDX-SBOM")
    if document.get("specVersion") not in SUPPORTED_SPEC_VERSIONS:
        raise InvalidSbomError(
            "CycloneDX-Version wird nicht unterstützt "
            f"({SUPPORTED_SPEC_VERSIONS[0]} bis {SUPPORTED_SPEC_VERSIONS[-1]})"
        )
    components = document.get("components")
    if not isinstance(components, list):
        raise InvalidSbomError("SBOM enthält keine Komponentenliste")
    return components


def _walk_components(components: list[object]) -> Iterator[Mapping[str, object]]:
    for raw in components:
        component = _mapping(raw)
        yield component
        nested = component.get("components")
        if isinstance(nested, list):
            yield from _walk_components(nested)


def _package_from_purl(purl: str) -> _PackageId | None:
    if not purl.startswith("pkg:"):
        return None
    path = purl[len("pkg:") :].split("#", 1)[0].split("?", 1)[0].rsplit("@", 1)[0]
    purl_type, _, rest = path.partition("/")
    ecosystem = ecosystem_for_purl_type(purl_type)
    if ecosystem is None or not rest:
        return None
    parts = [unquote(part) for part in rest.split("/")]
    separator = ":" if ecosystem == Ecosystem.MAVEN else "/"
    return _PackageId(ecosystem, separator.join(parts))


def _package_id(purl: str | None, name: str) -> _PackageId:
    package = _package_from_purl(purl) if purl else None
    return package or _PackageId(None, name)


def _direct_refs(document: Mapping[str, object]) -> frozenset[str] | None:
    """Refs, von denen das Hauptprojekt direkt abhängt.

    None (alle gelten als direkt), wenn kein Graph oder kein Eintrag für das Hauptprojekt da ist.
    """
    root_ref = _text(_mapping(_mapping(document.get("metadata")).get("component")).get("bom-ref"))
    dependencies = document.get("dependencies")
    if root_ref is None or not isinstance(dependencies, list):
        return None
    for raw in dependencies:
        dependency = _mapping(raw)
        depends_on = dependency.get("dependsOn")
        if dependency.get("ref") == root_ref and isinstance(depends_on, list):
            return frozenset(ref for ref in depends_on if isinstance(ref, str))
    return None


def _is_direct(component: Mapping[str, object], direct_refs: frozenset[str] | None) -> bool:
    return direct_refs is None or component.get("bom-ref") in direct_refs


def _entry_from(
    component: Mapping[str, object], direct_refs: frozenset[str] | None
) -> SbomEntry | None:
    name = _text(component.get("name"))
    version = _text(component.get("version"))
    if name is None or version is None:
        return None
    purl = _text(component.get("purl"))
    package = _package_id(purl, name)
    if len(package.name) > COMPONENT_NAME_MAX_LENGTH or len(version) > COMPONENT_VERSION_MAX_LENGTH:
        return None
    category = Category.FRAMEWORK if component.get("type") == "framework" else Category.LIBRARY
    return SbomEntry(
        name=package.name,
        version=version,
        category=category,
        ecosystem=package.ecosystem,
        direct=_is_direct(component, direct_refs),
        purl=purl,
    )


def _suggested_label(document: Mapping[str, object]) -> str | None:
    metadata = _mapping(document.get("metadata"))
    return _text(_mapping(metadata.get("component")).get("version")) or _text(
        metadata.get("timestamp")
    )


def _serial_number(document: Mapping[str, object]) -> str | None:
    serial = _text(document.get("serialNumber"))
    return serial if serial and len(serial) <= SBOM_SERIAL_MAX_LENGTH else None


class CycloneDxParser:
    """Erfüllt den Port ``SbomParser`` für CycloneDX JSON 1.4 bis 1.7."""

    def parse(self, document: Mapping[str, object]) -> ParsedSbom:
        imported = [
            component
            for component in _walk_components(_validate_header(document))
            if component.get("type") in _IMPORTED_TYPES
        ]
        if len(imported) > SBOM_MAX_COMPONENTS:
            raise InvalidSbomError(f"SBOM enthält mehr als {SBOM_MAX_COMPONENTS} Komponenten")
        direct_refs = _direct_refs(document)
        entries = [_entry_from(component, direct_refs) for component in imported]
        valid = tuple(entry for entry in entries if entry is not None)
        return ParsedSbom(
            entries=valid,
            serial_number=_serial_number(document),
            suggested_label=_suggested_label(document),
            skipped=len(entries) - len(valid),
        )
