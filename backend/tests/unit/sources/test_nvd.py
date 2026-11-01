import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.domain.ports import AffectedPackage, RangeEvent
from app.infrastructure.sources.nvd import NvdSource
from tests.unit.sources.helpers import component, mock_client, status_client

_CVE = {
    "cve": {
        "id": "CVE-2024-21",
        "descriptions": [{"lang": "en", "value": "MariaDB crash"}],
        "metrics": {
            "cvssMetricV31": [{"cvssData": {"baseScore": 6.5}}],
            "cvssMetricV40": [{"cvssData": {"baseScore": 8.7}}],
        },
        "references": [{"url": "https://mariadb.org/x"}],
        "configurations": [
            {
                "nodes": [
                    {
                        "cpeMatch": [
                            {
                                "vulnerable": True,
                                "criteria": "cpe:2.3:a:mariadb:mariadb:*:*:*:*:*:*:*:*",
                                "versionStartIncluding": "11.4.0",
                                "versionEndExcluding": "11.4.5",
                            },
                            {
                                "vulnerable": True,
                                "criteria": "cpe:2.3:a:mariadb:mariadb:10.6.1:*:*:*:*:*:*:*",
                            },
                            {
                                "vulnerable": False,
                                "criteria": "cpe:2.3:o:linux:linux_kernel:*:*:*:*:*:*:*:*",
                            },
                        ]
                    }
                ]
            }
        ],
    }
}


def _page(vulns: list[object], total: int, start: int = 0) -> dict[str, object]:
    return {
        "resultsPerPage": len(vulns),
        "startIndex": start,
        "totalResults": total,
        "vulnerabilities": vulns,
    }


def test_nvd_maps_record() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_page([_CVE], 1))

    vulns = NvdSource(mock_client(handler)).query(component("MariaDB", "11.4.2", None), None)
    assert seen[0].url.params["keywordSearch"] == "MariaDB"
    vuln = vulns[0]
    assert vuln.id == "CVE-2024-21"
    assert vuln.cvss_base == 8.7
    assert vuln.summary == "MariaDB crash"
    assert vuln.url == "https://nvd.nist.gov/vuln/detail/CVE-2024-21"
    assert vuln.affected == (
        AffectedPackage(
            None,
            "mariadb",
            (RangeEvent("introduced", "11.4.0"), RangeEvent("fixed", "11.4.5")),
        ),
        AffectedPackage(None, "mariadb", versions=("10.6.1",)),
    )


def test_nvd_sends_api_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_page([], 0))

    NvdSource(mock_client(handler)).query(component("redis", "7.2.0", None), "nvd-key")
    assert seen[0].headers["apiKey"] == "nvd-key"


def test_nvd_pages_through_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        start = int(request.url.params["startIndex"])
        cve = {"cve": {**_CVE["cve"], "id": f"CVE-2024-{start}"}}
        return httpx.Response(200, json=_page([cve], 2, start))

    vulns = NvdSource(mock_client(handler), page_size=1).query(
        component("mariadb", "11.4.2", None), None
    )
    assert [vuln.id for vuln in vulns] == ["CVE-2024-0", "CVE-2024-1"]


def test_nvd_http_error_raises_source_access_error() -> None:
    with pytest.raises(SourceAccessError, match="API-Key"):
        NvdSource(status_client(403)).query(component("redis", "7.2.0", None), None)
