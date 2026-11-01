import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.infrastructure.sources.snyk import SnykSource
from tests.unit.sources.helpers import component, mock_client, status_client

_ISSUES = {
    "data": [
        {
            "id": "SNYK-JS-REACT-1",
            "type": "issue",
            "attributes": {
                "key": "SNYK-JS-REACT-1",
                "title": "Cross-site Scripting",
                "description": "d",
                "problems": [
                    {"id": "CVE-2024-8", "source": "CVE"},
                    {"id": "CWE-79", "source": "CWE"},
                ],
                "severities": [{"source": "Snyk", "score": 6.5, "vector": "CVSS:3.1/AV:N"}],
            },
        }
    ],
    "links": {},
}


def test_snyk_maps_record() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_ISSUES)

    vulns = SnykSource(mock_client(handler)).query(component("react", "18.2.0"), "org-1:tok")
    assert "/orgs/org-1/packages/pkg%3Anpm%2Freact%4018.2.0/issues" in str(seen[0].url)
    assert seen[0].url.params["version"]
    vuln = vulns[0]
    assert vuln.id == "SNYK-JS-REACT-1"
    assert vuln.aliases == ["CVE-2024-8"]
    assert vuln.cvss_base == 6.5
    assert vuln.url == "https://security.snyk.io/vuln/SNYK-JS-REACT-1"


def test_snyk_sends_api_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": []})

    SnykSource(mock_client(handler)).query(component("react", "18.2.0"), "org-1:tok")
    assert seen[0].headers["Authorization"] == "token tok"


def test_snyk_unknown_package_is_empty() -> None:
    assert SnykSource(status_client(404)).query(component("x", "1.0"), "org-1:tok") == []


def test_snyk_without_required_key_raises() -> None:
    with pytest.raises(SourceAccessError, match="API-Key"):
        SnykSource(status_client(200)).query(component("react", "18.2.0"), None)


def test_snyk_http_error_raises_source_access_error() -> None:
    with pytest.raises(SourceAccessError, match="API-Key"):
        SnykSource(status_client(403)).query(component("react", "18.2.0"), "org-1:tok")
