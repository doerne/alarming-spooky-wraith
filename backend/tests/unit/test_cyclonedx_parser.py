import pytest

from app.domain.errors import InvalidSbomError
from app.domain.inventory import (
    COMPONENT_NAME_MAX_LENGTH,
    COMPONENT_VERSION_MAX_LENGTH,
    Category,
    Ecosystem,
)
from app.domain.sbom import SBOM_MAX_COMPONENTS, SBOM_SERIAL_MAX_LENGTH, SbomEntry
from app.infrastructure.sbom.cyclonedx import CycloneDxParser
from app.infrastructure.sources.purl import PURL_ECOSYSTEMS, ecosystem_for_purl_type


def _document(components: list[dict[str, object]], **extra: object) -> dict[str, object]:
    return {"bomFormat": "CycloneDX", "specVersion": "1.6", "components": components, **extra}


def _library(name: str, version: str | None, purl: str | None = None) -> dict[str, object]:
    component: dict[str, object] = {"type": "library", "name": name, "bom-ref": name}
    if version is not None:
        component["version"] = version
    if purl is not None:
        component["purl"] = purl
    return component


def _single(component: dict[str, object]) -> SbomEntry:
    parsed = CycloneDxParser().parse(_document([component]))
    assert len(parsed.entries) == 1
    return parsed.entries[0]


def test_parses_npm_scoped_package() -> None:
    entry = _single(_library("react-query", "5.0.0", "pkg:npm/%40tanstack/react-query@5.0.0"))
    assert entry == SbomEntry(
        name="@tanstack/react-query",
        version="5.0.0",
        category=Category.LIBRARY,
        ecosystem=Ecosystem.NPM,
        direct=True,
        purl="pkg:npm/%40tanstack/react-query@5.0.0",
    )


def test_parses_pypi_and_maven() -> None:
    pypi = _single(_library("fastapi", "0.115.0", "pkg:pypi/fastapi@0.115.0"))
    maven = _single(
        _library(
            "log4j-core",
            "2.14.1",
            "pkg:maven/org.apache.logging.log4j/log4j-core@2.14.1?type=jar",
        )
    )
    assert (pypi.name, pypi.ecosystem) == ("fastapi", Ecosystem.PYPI)
    assert (maven.name, maven.ecosystem) == ("org.apache.logging.log4j:log4j-core", Ecosystem.MAVEN)


def test_parses_go_module_path() -> None:
    entry = _single(_library("net", "0.17.0", "pkg:golang/golang.org/x/net@0.17.0"))
    assert (entry.name, entry.ecosystem) == ("golang.org/x/net", Ecosystem.GO)


def test_os_package_is_unchecked() -> None:
    entry = _single(
        _library(
            "openssl", "3.0.11-1", "pkg:deb/debian/openssl@3.0.11-1?arch=amd64&distro=debian-12"
        )
    )
    assert entry.ecosystem is None
    assert entry.checked is False
    assert entry.name == "openssl"


def test_component_without_purl_is_unchecked() -> None:
    entry = _single(_library("mystery", "1.0"))
    assert entry.ecosystem is None
    assert entry.name == "mystery"


def test_framework_type_maps_to_framework_category() -> None:
    component = _library("django", "5.0", "pkg:pypi/django@5.0")
    component["type"] = "framework"
    assert _single(component).category == Category.FRAMEWORK


def test_reads_nested_components_and_ignores_other_types() -> None:
    nested = _library("parent", "1.0", "pkg:npm/parent@1.0")
    nested["components"] = [_library("child", "2.0", "pkg:npm/child@2.0")]
    os_component: dict[str, object] = {
        "type": "operating-system",
        "name": "debian",
        "version": "12",
    }
    parsed = CycloneDxParser().parse(_document([nested, os_component]))
    assert [entry.name for entry in parsed.entries] == ["parent", "child"]
    assert parsed.skipped == 0


def test_direct_from_dependency_graph() -> None:
    document = _document(
        [_library("a", "1.0", "pkg:npm/a@1.0"), _library("b", "1.0", "pkg:npm/b@1.0")],
        metadata={"component": {"type": "application", "name": "app", "bom-ref": "root"}},
        dependencies=[{"ref": "root", "dependsOn": ["a"]}, {"ref": "a", "dependsOn": ["b"]}],
    )
    entries = {entry.name: entry for entry in CycloneDxParser().parse(document).entries}
    assert entries["a"].direct is True
    assert entries["b"].direct is False


def test_all_direct_without_graph() -> None:
    document = _document(
        [_library("a", "1.0", "pkg:npm/a@1.0"), _library("b", "1.0", "pkg:npm/b@1.0")],
        metadata={"component": {"type": "application", "name": "app", "bom-ref": "root"}},
    )
    assert all(entry.direct for entry in CycloneDxParser().parse(document).entries)


def test_all_direct_when_graph_lacks_root_entry() -> None:
    document = _document(
        [_library("a", "1.0", "pkg:npm/a@1.0"), _library("b", "1.0", "pkg:npm/b@1.0")],
        metadata={"component": {"type": "application", "name": "app", "bom-ref": "root"}},
        dependencies=[{"ref": "a", "dependsOn": ["b"]}],
    )
    assert all(entry.direct for entry in CycloneDxParser().parse(document).entries)


def test_skips_components_without_version_or_too_long() -> None:
    parsed = CycloneDxParser().parse(
        _document(
            [
                _library("no-version", None),
                _library("x" * (COMPONENT_NAME_MAX_LENGTH + 1), "1.0"),
                _library("long-version", "1" * (COMPONENT_VERSION_MAX_LENGTH + 1)),
                _library("ok", "1.0"),
            ]
        )
    )
    assert [entry.name for entry in parsed.entries] == ["ok"]
    assert parsed.skipped == 3


def test_suggested_label_prefers_root_version() -> None:
    with_version = _document(
        [], metadata={"timestamp": "2026-11-21T10:00:00Z", "component": {"version": "1.4.0"}}
    )
    without_version = _document([], metadata={"timestamp": "2026-11-21T10:00:00Z"})
    assert CycloneDxParser().parse(with_version).suggested_label == "1.4.0"
    assert CycloneDxParser().parse(without_version).suggested_label == "2026-11-21T10:00:00Z"
    assert CycloneDxParser().parse(_document([])).suggested_label is None


def test_reads_serial_number_and_drops_too_long() -> None:
    assert CycloneDxParser().parse(_document([], serialNumber="urn:uuid:1")).serial_number == (
        "urn:uuid:1"
    )
    assert (
        CycloneDxParser()
        .parse(_document([], serialNumber="u" * (SBOM_SERIAL_MAX_LENGTH + 1)))
        .serial_number
        is None
    )


@pytest.mark.parametrize(
    "document",
    [
        {"spdxVersion": "SPDX-2.3"},
        {"bomFormat": "CycloneDX", "specVersion": "1.2", "components": []},
        {"bomFormat": "CycloneDX", "specVersion": "1.6"},
        {"bomFormat": "CycloneDX", "specVersion": "1.6", "components": "nope"},
    ],
)
def test_rejects_wrong_format(document: dict[str, object]) -> None:
    with pytest.raises(InvalidSbomError):
        CycloneDxParser().parse(document)


def test_rejects_too_many_components() -> None:
    components = [_library(f"p{index}", "1.0") for index in range(SBOM_MAX_COMPONENTS + 1)]
    with pytest.raises(InvalidSbomError):
        CycloneDxParser().parse(_document(components))


def test_purl_type_mapping_roundtrip() -> None:
    for value in PURL_ECOSYSTEMS:
        ecosystem = Ecosystem(value)
        purl_type = {
            Ecosystem.NPM: "npm",
            Ecosystem.PYPI: "pypi",
            Ecosystem.MAVEN: "maven",
            Ecosystem.RUBYGEMS: "gem",
            Ecosystem.GO: "golang",
            Ecosystem.CRATES_IO: "cargo",
            Ecosystem.NUGET: "nuget",
            Ecosystem.PACKAGIST: "composer",
            Ecosystem.CRAN: "cran",
        }[ecosystem]
        assert ecosystem_for_purl_type(purl_type) == ecosystem
    assert ecosystem_for_purl_type("deb") is None
