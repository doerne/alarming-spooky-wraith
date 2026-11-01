import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.domain.ports import AffectedPackage
from app.infrastructure.sources.cvedetails import CvedetailsSource
from tests.unit.sources.helpers import component, mock_client, status_client

_RESULT = {
    "results": [
        {
            "cveId": "CVE-2024-31",
            "summary": "Redis overflow",
            "maxCvssBaseScore": 7.2,
        }
    ]
}


def test_cvedetails_maps_record() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_RESULT)

    vulns = CvedetailsSource(mock_client(handler)).query(component("redis", "7.2.0", None), "t")
    assert seen[0].url.params["productName"] == "redis"
    assert seen[0].url.params["versionString"] == "7.2.0"
    vuln = vulns[0]
    assert vuln.id == "CVE-2024-31"
    assert vuln.cvss_base == 7.2
    assert vuln.url == "https://www.cvedetails.com/cve/CVE-2024-31/"
    assert vuln.affected == (AffectedPackage(None, "redis", versions=("7.2.0",)),)


def test_cvedetails_sends_api_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"results": []})

    CvedetailsSource(mock_client(handler)).query(component("redis", "7.2.0", None), "tok")
    assert seen[0].headers["Authorization"] == "Bearer tok"


def test_cvedetails_without_required_key_raises() -> None:
    with pytest.raises(SourceAccessError, match="API-Key"):
        CvedetailsSource(status_client(200)).query(component("redis", "7.2.0", None), None)


def test_cvedetails_http_error_raises_source_access_error() -> None:
    with pytest.raises(SourceAccessError, match="API-Key"):
        CvedetailsSource(status_client(401)).query(component("redis", "7.2.0", None), "tok")
