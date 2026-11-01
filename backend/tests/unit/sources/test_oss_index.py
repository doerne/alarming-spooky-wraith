import base64

import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.infrastructure.sources.oss_index import OssIndexSource
from tests.unit.sources.helpers import component, mock_client, status_client

_REPORT = [
    {
        "coordinates": "pkg:npm/react@18.2.0",
        "vulnerabilities": [
            {
                "id": "sonatype-2024-1",
                "displayName": "CVE-2024-7",
                "title": "[CVE-2024-7] XSS",
                "description": "d",
                "cvssScore": 6.1,
                "cvssVector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
                "cve": "CVE-2024-7",
                "reference": "https://ossindex.sonatype.org/vulnerability/sonatype-2024-1",
                "externalReferences": ["https://example.org/x"],
            }
        ],
    }
]


def test_oss_index_maps_record() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_REPORT)

    vulns = OssIndexSource(mock_client(handler)).query(component("react", "18.2.0"), "me:tok")
    assert vulns[0].id == "sonatype-2024-1"
    assert vulns[0].aliases == ["CVE-2024-7"]
    assert vulns[0].cvss_base == 6.1
    assert vulns[0].url == "https://ossindex.sonatype.org/vulnerability/sonatype-2024-1"
    assert b"pkg:npm/react@18.2.0" in seen[0].content


def test_oss_index_sends_api_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    OssIndexSource(mock_client(handler)).query(component("react", "18.2.0"), "me:tok")
    expected = "Basic " + base64.b64encode(b"me:tok").decode()
    assert seen[0].headers["Authorization"] == expected


def test_oss_index_without_required_key_raises() -> None:
    with pytest.raises(SourceAccessError, match="API-Key"):
        OssIndexSource(status_client(200)).query(component("react", "18.2.0"), None)


def test_oss_index_malformed_key_raises() -> None:
    with pytest.raises(SourceAccessError, match="Format"):
        OssIndexSource(status_client(200)).query(component("react", "18.2.0"), "nocolon")


def test_oss_index_http_error_raises_source_access_error() -> None:
    with pytest.raises(SourceAccessError, match="API-Key"):
        OssIndexSource(status_client(401)).query(component("react", "18.2.0"), "me:tok")
