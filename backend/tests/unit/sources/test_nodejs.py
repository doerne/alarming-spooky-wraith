import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.domain.ports import AffectedPackage, RangeEvent
from app.infrastructure.sources.nodejs import NodejsSource, npm_range_events
from app.infrastructure.univers_matcher import UniversVersionMatcher
from tests.unit.sources.helpers import mock_client, status_client

_INDEX = {
    "1": {
        "cve": ["CVE-2026-3001"],
        "vulnerable": "<18.20.4 || >=20.0.0 <20.15.1",
        "patched": "^18.20.4 || ^20.15.1",
        "ref": "https://nodejs.org/en/blog/vulnerability/july-2026",
        "overview": "HTTP request smuggling",
    },
    "2": {"cve": [], "vulnerable": "4.x", "overview": "Old issue"},
}


def test_nodejs_maps_record() -> None:
    client = mock_client(lambda _: httpx.Response(200, json=_INDEX))
    vulns = NodejsSource(client).load(None, frozenset({"node.js"}))
    assert [vuln.id for vuln in vulns] == ["CVE-2026-3001", "NSWG-CORE-2"]
    vuln = vulns[0]
    assert vuln.summary == "HTTP request smuggling"
    assert vuln.url == "https://nodejs.org/en/blog/vulnerability/july-2026"
    assert {package.name for package in vuln.affected} == {"node.js", "nodejs", "node"}


def test_npm_range_events() -> None:
    assert npm_range_events("4.x") == (
        RangeEvent("introduced", "4.0.0"),
        RangeEvent("fixed", "5.0.0"),
    )
    assert npm_range_events("^6.2.0") == (
        RangeEvent("introduced", "6.2.0"),
        RangeEvent("fixed", "7.0.0"),
    )


@pytest.mark.parametrize(
    ("version", "affected"),
    [("18.20.3", True), ("18.20.4", False), ("20.15.0", True), ("22.1.0", False)],
)
def test_nodejs_ranges_match(version: str, affected: bool) -> None:
    events = npm_range_events("<18.20.4 || >=20.0.0 <20.15.1")
    package = AffectedPackage(None, "node.js", events)
    assert UniversVersionMatcher().is_affected("npm", version, package) is affected


def test_nodejs_without_names_does_not_download() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("darf nicht laden")

    assert NodejsSource(mock_client(handler)).load(None, frozenset()) == []


def test_nodejs_http_error_raises_source_access_error() -> None:
    with pytest.raises(SourceAccessError, match="nicht erreichbar"):
        NodejsSource(status_client(500)).load(None, frozenset({"node.js"}))
