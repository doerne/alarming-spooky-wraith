import pytest

from app.domain.errors import SourceAccessError
from app.domain.inventory import Ecosystem
from app.domain.ports import RangeEvent
from app.infrastructure.sources.packagist import PackagistSource, composer_constraint_events
from app.infrastructure.univers_matcher import UniversVersionMatcher
from tests.unit.sources.helpers import component, mock_client, status_client

_RESPONSE = {
    "advisories": {
        "symfony/http-kernel": [
            {
                "advisoryId": "PKSA-1",
                "remoteId": "GHSA-x",
                "title": "Cache poisoning",
                "link": "https://symfony.com/cve-2024-1",
                "cve": "CVE-2024-1",
                "affectedVersions": ">=5.0.0,<5.4.20|>=6.0.0,<6.2.6",
            },
            {
                "advisoryId": "PKSA-2",
                "remoteId": "GHSA-y",
                "title": "Old bug",
                "link": "https://symfony.com/cve-2019-1",
                "cve": None,
                "affectedVersions": "<4.0.0",
            },
        ]
    }
}


def _source() -> PackagistSource:
    return PackagistSource(
        mock_client(lambda _: __import__("httpx").Response(200, json=_RESPONSE)),
        UniversVersionMatcher(),
    )


def test_packagist_maps_record() -> None:
    kernel = component("symfony/http-kernel", "6.2.5", Ecosystem.PACKAGIST)
    vulns = _source().query(kernel, None)
    assert [vuln.id for vuln in vulns] == ["PKSA-1"]
    assert vulns[0].aliases == ["CVE-2024-1", "GHSA-x"]
    assert vulns[0].url == "https://symfony.com/cve-2024-1"


def test_packagist_returns_nothing_for_safe_version() -> None:
    kernel = component("symfony/http-kernel", "6.2.6", Ecosystem.PACKAGIST)
    assert _source().query(kernel, None) == []


def test_composer_constraint_events() -> None:
    assert composer_constraint_events(">=5.0.0,<5.4.20") == (
        RangeEvent("introduced", "5.0.0"),
        RangeEvent("fixed", "5.4.20"),
    )
    assert composer_constraint_events("<=1.2.3") == (
        RangeEvent("introduced", "0"),
        RangeEvent("last_affected", "1.2.3"),
    )


def test_packagist_http_error_raises_source_access_error() -> None:
    source = PackagistSource(status_client(500), UniversVersionMatcher())
    with pytest.raises(SourceAccessError, match="nicht erreichbar"):
        source.query(component("a/b", "1.0", Ecosystem.PACKAGIST), None)
