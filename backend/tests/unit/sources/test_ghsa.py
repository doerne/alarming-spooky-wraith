import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.domain.inventory import Ecosystem
from app.domain.ports import AffectedPackage, RangeEvent
from app.infrastructure.sources.ghsa import GhsaSource
from tests.unit.sources.helpers import component, mock_client, status_client

_ADVISORY = {
    "ghsa_id": "GHSA-aaaa-bbbb-cccc",
    "cve_id": "CVE-2024-11",
    "summary": "Prototype pollution",
    "description": "long",
    "html_url": "https://github.com/advisories/GHSA-aaaa-bbbb-cccc",
    "references": ["https://example.org/r"],
    "cvss_severities": {
        "cvss_v3": {"vector_string": None, "score": 7.5},
        "cvss_v4": {"vector_string": None, "score": None},
    },
    "vulnerabilities": [
        {
            "package": {"ecosystem": "npm", "name": "react"},
            "vulnerable_version_range": ">= 18.0.0, < 18.2.1",
            "first_patched_version": "18.2.1",
        }
    ],
}


def test_ghsa_maps_record() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[_ADVISORY])

    vulns = GhsaSource(mock_client(handler)).query(component("react", "18.2.0"), None)
    assert seen[0].url.params["ecosystem"] == "npm"
    assert seen[0].url.params["affects"] == "react@18.2.0"
    assert "Authorization" not in seen[0].headers
    vuln = vulns[0]
    assert vuln.id == "GHSA-aaaa-bbbb-cccc"
    assert vuln.aliases == ["CVE-2024-11"]
    assert vuln.cvss_base == 7.5
    assert vuln.fixed_version == "18.2.1"
    assert vuln.url == "https://github.com/advisories/GHSA-aaaa-bbbb-cccc"
    assert vuln.affected == (
        AffectedPackage(
            "npm", "react", (RangeEvent("introduced", "18.0.0"), RangeEvent("fixed", "18.2.1"))
        ),
    )


def test_ghsa_sends_api_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    GhsaSource(mock_client(handler)).query(component("requests", "2.0", Ecosystem.PYPI), "tok")
    assert seen[0].headers["Authorization"] == "Bearer tok"
    assert seen[0].url.params["ecosystem"] == "pip"


def test_ghsa_follows_next_page() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "after" in request.url.params:
            return httpx.Response(200, json=[{**_ADVISORY, "ghsa_id": "GHSA-2"}])
        link = '<https://api.github.com/advisories?after=x>; rel="next"'
        return httpx.Response(200, json=[_ADVISORY], headers={"Link": link})

    vulns = GhsaSource(mock_client(handler)).query(component("react", "18.2.0"), None)
    assert [vuln.id for vuln in vulns] == ["GHSA-aaaa-bbbb-cccc", "GHSA-2"]


def test_ghsa_http_error_raises_source_access_error() -> None:
    with pytest.raises(SourceAccessError, match="Rate-Limit"):
        GhsaSource(status_client(429)).query(component("react", "18.2.0"), None)
