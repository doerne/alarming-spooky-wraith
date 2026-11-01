import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.domain.ports import AffectedPackage, RangeEvent
from app.infrastructure.sources.euvd import EuvdSource, euvd_version_events
from tests.unit.sources.helpers import component, mock_client, status_client

_ITEM = {
    "id": "EUVD-2026-1",
    "description": "Connector bug",
    "baseScore": 5.9,
    "references": "https://a.example\nhttps://b.example\n",
    "aliases": "CVE-2026-9\nGHSA-h599\n",
    "enisaIdProduct": [
        {"product": {"name": "mariadb"}, "product_version": "11.4.0, < 11.4.5"},
        {"product": {"name": "mariadb"}, "product_version": "<= 10.6.2"},
    ],
}


def test_euvd_maps_record() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"items": [_ITEM], "total": 1})

    vulns = EuvdSource(mock_client(handler)).query(component("MariaDB", "11.4.2", None), None)
    assert seen[0].url.params["product"] == "MariaDB"
    vuln = vulns[0]
    assert vuln.id == "EUVD-2026-1"
    assert vuln.aliases == ["CVE-2026-9", "GHSA-h599"]
    assert vuln.references == ["https://a.example", "https://b.example"]
    assert vuln.cvss_base == 5.9
    assert vuln.url == "https://euvd.enisa.europa.eu/vulnerability/EUVD-2026-1"
    assert vuln.affected[0] == AffectedPackage(
        None, "mariadb", (RangeEvent("introduced", "11.4.0"), RangeEvent("fixed", "11.4.5"))
    )


def test_euvd_version_events() -> None:
    assert euvd_version_events("<= 10.6.2") == (
        (RangeEvent("introduced", "0"), RangeEvent("last_affected", "10.6.2")),
        (),
    )
    assert euvd_version_events("5.0.1") == ((), ("5.0.1",))


def test_euvd_http_error_raises_source_access_error() -> None:
    with pytest.raises(SourceAccessError, match="nicht erreichbar"):
        EuvdSource(status_client(502)).query(component("redis", "7.2.0", None), None)
