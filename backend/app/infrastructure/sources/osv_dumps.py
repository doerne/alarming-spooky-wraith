"""Sprach-Datenbanken, die ihre Advisories an OSV.dev liefern.

Statt jedes Repo einzeln zu parsen, laden wir den OSV-Abzug des Ökosystems
(``<ökosystem>/all.zip``) und behalten nur Einträge mit dem ID-Präfix der
jeweiligen Datenbank (PYSEC-, GO-, RUSTSEC- …). So stammen die Daten aus
genau dieser Datenbank, liegen aber schon einheitlich im OSV-Format vor.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass

from app.domain.ports import SourceVuln
from app.domain.sources import MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.archives import open_archive
from app.infrastructure.sources.http_cache import HttpCache
from app.infrastructure.sources.names import normalize_pypi
from app.infrastructure.sources.osv_format import parse_osv_record

_DUMP_URL = "https://osv-vulnerabilities.storage.googleapis.com/{ecosystem}/all.zip"


@dataclass(frozen=True)
class _Dump:
    key: str
    name: str
    homepage_url: str
    description: str
    ecosystem: str
    id_prefix: str


_DUMPS = (
    _Dump("pypa", "PyPI Advisory Database", "https://github.com/pypa/advisory-database",
          "Advisories der Python Packaging Authority für PyPI-Pakete.", "PyPI", "PYSEC-"),
    _Dump("go-vulndb", "Go Vulnerability Database", "https://pkg.go.dev/vuln",
          "Offizielle Schwachstellen-Datenbank des Go-Teams.", "Go", "GO-"),
    _Dump("rustsec", "RustSec", "https://rustsec.org",
          "Advisory-Datenbank für Rust-Crates.", "crates.io", "RUSTSEC-"),
    _Dump("haskell", "Haskell Security Advisories", "https://github.com/haskell/security-advisories",
          "Advisories der Haskell Security Response Team für Hackage.", "Hackage", "HSEC-"),
    _Dump("rconsortium", "R Consortium Advisory DB",
          "https://github.com/RConsortium/r-advisory-database",
          "Advisory-Datenbank des R Consortium für CRAN-Pakete.", "CRAN", "RSEC-"),
    _Dump("opam", "OCaml opam Advisories", "https://github.com/ocaml/security-advisories",
          "Security-Advisories für OCaml-Pakete aus opam.", "opam", "OSEC-"),
)  # fmt: skip

OSV_DUMP_DESCRIPTORS: dict[str, SourceDescriptor] = {
    dump.key: SourceDescriptor(
        key=dump.key,
        name=dump.name,
        homepage_url=dump.homepage_url,
        description=dump.description,
        kind=SourceKind.BULK,
        scope=MatchScope.PACKAGE,
        ecosystems=frozenset({dump.ecosystem}),
    )
    for dump in _DUMPS
}
_DUMP_BY_KEY = {dump.key: dump for dump in _DUMPS}


def _package_names(raw: Mapping[str, object], ecosystem: str) -> set[str]:
    names = set()
    for item in raw.get("affected") or []:  # type: ignore[attr-defined]
        name = str((item.get("package") or {}).get("name") or "").lower()
        names.add(normalize_pypi(name) if ecosystem == "PyPI" else name)
    return names


class OsvDumpSource:
    def __init__(self, descriptor: SourceDescriptor, cache: HttpCache) -> None:
        self.descriptor = descriptor
        self._dump = _DUMP_BY_KEY[descriptor.key]
        self._cache = cache

    def load(self, api_key: str | None, names: frozenset[str]) -> list[SourceVuln]:  # noqa: ARG002 - kein Key nötig
        if not names:
            return []
        url = _DUMP_URL.format(ecosystem=self._dump.ecosystem)
        path = self._cache.fetch(self.descriptor.key, url)
        vulns: list[SourceVuln] = []
        with open_archive(path, self.descriptor.name) as archive:
            for entry in archive.namelist():
                if not entry.startswith(self._dump.id_prefix):
                    continue
                raw = json.loads(archive.read(entry))
                if _package_names(raw, self._dump.ecosystem) & names:
                    vulns.append(parse_osv_record(raw, self.descriptor.key))
        return vulns
