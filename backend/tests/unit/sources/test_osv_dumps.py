import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.infrastructure.sources.http_cache import HttpCache
from app.infrastructure.sources.osv_dumps import OSV_DUMP_DESCRIPTORS, OsvDumpSource
from tests.unit.sources.helpers import mock_client


def _record(vuln_id: str, ecosystem: str, name: str) -> dict[str, object]:
    return {
        "id": vuln_id,
        "aliases": ["CVE-2024-40"],
        "summary": "bad",
        "affected": [
            {
                "package": {"ecosystem": ecosystem, "name": name},
                "ranges": [
                    {"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "2.0"}]}
                ],
            }
        ],
    }


def _zip(records: list[dict[str, object]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for record in records:
            archive.writestr(f"{record['id']}.json", json.dumps(record))
    return buffer.getvalue()


def _source(key: str, tmp_path: Path, payload: bytes, seen: list[str]) -> OsvDumpSource:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=payload)

    client = mock_client(handler)
    return OsvDumpSource(OSV_DUMP_DESCRIPTORS[key], HttpCache(tmp_path, client))


@pytest.mark.parametrize(
    ("key", "ecosystem", "own_id", "foreign_id"),
    [
        ("pypa", "PyPI", "PYSEC-2024-1", "GHSA-x"),
        ("go-vulndb", "Go", "GO-2024-1", "GHSA-x"),
        ("rustsec", "crates.io", "RUSTSEC-2024-1", "GHSA-x"),
        ("haskell", "Hackage", "HSEC-2024-1", "GHSA-x"),
        ("rconsortium", "CRAN", "RSEC-2024-1", "GHSA-x"),
        ("opam", "opam", "OSEC-2024-1", "GHSA-x"),
    ],
)
def test_dump_maps_only_own_records(
    key: str, ecosystem: str, own_id: str, foreign_id: str, tmp_path: Path
) -> None:
    payload = _zip(
        [
            _record(own_id, ecosystem, "pkg"),
            _record(foreign_id, ecosystem, "pkg"),
            _record(f"{own_id}9", ecosystem, "other"),
        ]
    )
    seen: list[str] = []
    vulns = _source(key, tmp_path, payload, seen).load(None, frozenset({"pkg"}))
    assert seen == [f"https://osv-vulnerabilities.storage.googleapis.com/{ecosystem}/all.zip"]
    assert [vuln.id for vuln in vulns] == [own_id]
    assert vulns[0].source_key == key
    assert vulns[0].fixed_version == "2.0"


def test_dump_matches_pypi_names_normalized(tmp_path: Path) -> None:
    payload = _zip([_record("PYSEC-2024-2", "PyPI", "Django_Rest")])
    vulns = _source("pypa", tmp_path, payload, []).load(None, frozenset({"django-rest"}))
    assert [vuln.id for vuln in vulns] == ["PYSEC-2024-2"]


def test_dump_without_names_does_not_download(tmp_path: Path) -> None:
    seen: list[str] = []
    assert _source("pypa", tmp_path, b"", seen).load(None, frozenset()) == []
    assert seen == []


def test_dump_http_error_raises_source_access_error(tmp_path: Path) -> None:
    client = mock_client(lambda _: httpx.Response(500))
    source = OsvDumpSource(OSV_DUMP_DESCRIPTORS["rustsec"], HttpCache(tmp_path, client))
    with pytest.raises(SourceAccessError, match="nicht erreichbar"):
        source.load(None, frozenset({"serde"}))


def test_broken_zip_raises_source_access_error(tmp_path: Path) -> None:
    source = _source("opam", tmp_path, b"not a zip", [])
    with pytest.raises(SourceAccessError, match="beschädigt"):
        source.load(None, frozenset({"lwt"}))
