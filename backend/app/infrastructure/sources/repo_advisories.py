"""Security-Advisories einzelner Framework-Repos auf GitHub (Symfony, Laravel).

Strukturierter als die Blogs; Treffer laufen trotzdem über den Namen
(„symfony“, „laravel“ oder die Composer-Paketnamen), ohne Versionsprüfung.
"""

from dataclasses import replace
from typing import ClassVar

import httpx

from app.domain.ports import AffectedPackage, SourceVuln
from app.domain.sources import ApiKeyRequirement, MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.ghsa import parse_github_advisory
from app.infrastructure.sources.http_errors import send

_PAGE_SIZE = 100
_MAX_PAGES = 10
_PACKAGIST = "Packagist"
_TOKEN_HINT = "GitHub-Token (optional, hebt das Rate-Limit)"


class _RepoAdvisorySource:
    descriptor: ClassVar[SourceDescriptor]
    repository: ClassVar[str]
    product_name: ClassVar[str]

    def __init__(self, client: httpx.Client, base_url: str = "https://api.github.com") -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    def load(self, api_key: str | None, names: frozenset[str]) -> list[SourceVuln]:
        if not names:
            return []
        headers = {"Accept": "application/vnd.github+json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        url: str | None = f"{self._base_url}/repos/{self.repository}/security-advisories"
        params: dict[str, str] | None = {"per_page": str(_PAGE_SIZE), "state": "published"}
        vulns: list[SourceVuln] = []
        for _ in range(_MAX_PAGES):
            if url is None:
                break
            response = send(self._client, "GET", url, params=params, headers=headers)
            vulns += [self._to_vuln(item) for item in response.json()]
            url = response.links.get("next", {}).get("url")
            params = None
        return vulns

    def _to_vuln(self, advisory: dict[str, object]) -> SourceVuln:
        vuln = parse_github_advisory(advisory, self.descriptor.key, _PACKAGIST)
        product = AffectedPackage(None, self.product_name)
        packages = tuple(AffectedPackage(None, package.name) for package in vuln.affected)
        return replace(vuln, affected=(product, *packages))


def _descriptor(key: str, name: str, homepage_url: str, product: str) -> SourceDescriptor:
    return SourceDescriptor(
        key=key,
        name=name,
        homepage_url=homepage_url,
        description=f"GitHub-Security-Advisories des {name.split(maxsplit=1)[0]}-Repos; "
        f"Treffer über „{product}“ bzw. die Composer-Pakete, ohne Versionsprüfung.",
        kind=SourceKind.BULK,
        scope=MatchScope.NAME,
        api_key_requirement=ApiKeyRequirement.OPTIONAL,
        api_key_hint=_TOKEN_HINT,
    )


class SymfonySource(_RepoAdvisorySource):
    descriptor = _descriptor(
        "symfony", "Symfony Security", "https://symfony.com/blog/category/security-advisories",
        "symfony",
    )  # fmt: skip
    repository = "symfony/symfony"
    product_name = "symfony"


class LaravelSource(_RepoAdvisorySource):
    descriptor = _descriptor(
        "laravel", "Laravel Security", "https://github.com/laravel/framework/security", "laravel"
    )
    repository = "laravel/framework"
    product_name = "laravel"
