from typing import Any

import httpx
import pytest

from app.infrastructure.osv_client import HttpxOsvClient

_RESPONSE = {
    "vulns": [
        {
            "id": "GHSA-x",
            "aliases": ["CVE-2024-1"],
            "summary": "s",
            "details": "d",
            "severity": [
                {
                    "type": "CVSS_V3",
                    "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                }
            ],
            "affected": [{"ranges": [{"events": [{"introduced": "0"}, {"fixed": "18.2.1"}]}]}],
            "references": [{"url": "https://x"}],
        }
    ]
}


def _client(response: dict[str, Any]) -> HttpxOsvClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/query"
        return httpx.Response(200, json=response)

    transport = httpx.MockTransport(handler)
    return HttpxOsvClient("https://api.osv.dev", httpx.Client(transport=transport))


def test_query_maps_osv_response() -> None:
    vulns = _client(_RESPONSE).query("npm", "react", "18.2.0")
    assert len(vulns) == 1
    assert vulns[0].id == "GHSA-x"
    assert vulns[0].aliases == ["CVE-2024-1"]
    assert vulns[0].cvss_base == pytest.approx(9.8)
    assert vulns[0].fixed_version == "18.2.1"
    assert vulns[0].references == ["https://x"]


def test_query_without_severity_has_no_cvss() -> None:
    response = {"vulns": [{"id": "GHSA-y", "summary": "s"}]}
    vulns = _client(response).query("npm", "left-pad", "1.0.0")
    assert vulns[0].cvss_base is None
    assert vulns[0].fixed_version is None


def test_empty_response_yields_no_vulns() -> None:
    assert _client({}).query("npm", "react", "18.2.0") == []
