import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.infrastructure.sources.repo_advisories import LaravelSource, SymfonySource
from tests.unit.sources.helpers import mock_client, status_client

_ADVISORY = {
    "ghsa_id": "GHSA-lara-0001",
    "cve_id": "CVE-2026-2001",
    "summary": "Mass assignment",
    "description": "long",
    "html_url": "https://github.com/laravel/framework/security/advisories/GHSA-lara-0001",
    "cvss_severities": {"cvss_v3": {"score": 8.1}},
    "vulnerabilities": [
        {
            "package": {"ecosystem": "composer", "name": "laravel/framework"},
            "vulnerable_version_range": "< 11.0.5",
            "patched_versions": "11.0.5",
        }
    ],
}


def test_laravel_maps_record() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[_ADVISORY])

    vulns = LaravelSource(mock_client(handler)).load(None, frozenset({"laravel"}))
    assert seen[0].url.path == "/repos/laravel/framework/security-advisories"
    vuln = vulns[0]
    assert vuln.id == "GHSA-lara-0001"
    assert vuln.aliases == ["CVE-2026-2001"]
    assert vuln.cvss_base == 8.1
    assert {package.name for package in vuln.affected} == {"laravel", "laravel/framework"}


def test_symfony_uses_symfony_repo() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    SymfonySource(mock_client(handler)).load("tok", frozenset({"symfony"}))
    assert seen[0].url.path == "/repos/symfony/symfony/security-advisories"
    assert seen[0].headers["Authorization"] == "Bearer tok"


def test_repo_advisory_without_cve_keeps_ghsa() -> None:
    advisory = {**_ADVISORY, "cve_id": None}
    client = mock_client(lambda _: httpx.Response(200, json=[advisory]))
    assert LaravelSource(client).load(None, frozenset({"laravel"}))[0].aliases == []


def test_repo_advisories_http_error_raises_source_access_error() -> None:
    with pytest.raises(SourceAccessError, match="Rate-Limit"):
        LaravelSource(status_client(429)).load(None, frozenset({"laravel"}))
