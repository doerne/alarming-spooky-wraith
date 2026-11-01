import io
import zipfile
from pathlib import Path

import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.domain.ports import AffectedPackage, RangeEvent
from app.infrastructure.sources.http_cache import HttpCache
from app.infrastructure.sources.rubysec import RubysecSource, rubysec_events
from app.infrastructure.univers_matcher import UniversVersionMatcher
from tests.unit.sources.helpers import mock_client

_ADVISORY = """---
gem: actionpack
cve: 2024-1111
ghsa: abcd-efgh-ijkl
url: https://rubysec.example/actionpack
title: XSS in actionpack
description: |
  Long text.
cvss_v3: 6.1
patched_versions:
  - "~> 6.1.7, >= 6.1.7.7"
  - ">= 7.0.8.1"
unaffected_versions:
  - "< 5.0.0"
"""


def _zip(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(f"ruby-advisory-db-master/{name}", content)
    return buffer.getvalue()


def _source(tmp_path: Path, payload: bytes) -> RubysecSource:
    client = mock_client(lambda _: httpx.Response(200, content=payload))
    return RubysecSource(HttpCache(tmp_path, client))


def test_rubysec_maps_record(tmp_path: Path) -> None:
    payload = _zip(
        {
            "gems/actionpack/CVE-2024-1111.yml": _ADVISORY,
            "gems/rack/CVE-2024-2.yml": _ADVISORY.replace("actionpack", "rack"),
            "rubies/ruby/CVE-2024-3.yml": "engine: ruby\n",
        }
    )
    vulns = _source(tmp_path, payload).load(None, frozenset({"actionpack"}))
    assert len(vulns) == 1
    vuln = vulns[0]
    assert vuln.id == "CVE-2024-1111"
    assert vuln.aliases == ["GHSA-abcd-efgh-ijkl"]
    assert vuln.cvss_base == 6.1
    assert vuln.url == "https://rubysec.example/actionpack"
    assert vuln.affected[0].ecosystem == "RubyGems"


def test_rubysec_events_cover_patched_branches() -> None:
    events = rubysec_events(["~> 6.1.7, >= 6.1.7.7", ">= 7.0.8.1"], ["< 5.0.0"])
    assert events == (
        RangeEvent("introduced", "5.0.0"),
        RangeEvent("fixed", "6.1.7.7"),
        RangeEvent("introduced", "6.2"),
        RangeEvent("fixed", "7.0.8.1"),
    )


@pytest.mark.parametrize(
    ("version", "affected"),
    [("4.2.0", False), ("6.1.7.6", True), ("6.1.7.8", False), ("7.0.0", True), ("7.1.0", False)],
)
def test_rubysec_events_match_versions(version: str, affected: bool) -> None:
    events = rubysec_events(["~> 6.1.7, >= 6.1.7.7", ">= 7.0.8.1"], ["< 5.0.0"])
    package = AffectedPackage("RubyGems", "actionpack", events)
    assert UniversVersionMatcher().is_affected("RubyGems", version, package) is affected


def test_rubysec_http_error_raises_source_access_error(tmp_path: Path) -> None:
    client = mock_client(lambda _: httpx.Response(503))
    with pytest.raises(SourceAccessError, match="nicht erreichbar"):
        RubysecSource(HttpCache(tmp_path, client)).load(None, frozenset({"rack"}))
