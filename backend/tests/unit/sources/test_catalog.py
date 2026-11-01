import re
from pathlib import Path

import httpx

from app.domain.sources import ApiKeyRequirement
from app.infrastructure.sources.catalog import build_sources
from app.infrastructure.sources.http_cache import HttpCache
from app.infrastructure.univers_matcher import UniversVersionMatcher

_SPEC_KEYS = {
    "osv", "ghsa", "nvd", "cve-org", "euvd", "cvedetails", "snyk", "oss-index",
    "pypa", "go-vulndb", "rustsec", "rubysec", "packagist", "haskell", "rconsortium",
    "opam", "django", "spring", "nodejs", "symfony", "laravel",
}  # fmt: skip
_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _keys(tmp_path: Path) -> list[str]:
    client = httpx.Client()
    sources = build_sources(
        client, HttpCache(tmp_path, client), UniversVersionMatcher(), "https://api.osv.dev"
    )
    return [source.descriptor.key for source in sources]


def test_catalog_contains_all_spec_sources(tmp_path: Path) -> None:
    assert set(_keys(tmp_path)) == _SPEC_KEYS


def test_catalog_keys_are_unique_and_kebab_case(tmp_path: Path) -> None:
    keys = _keys(tmp_path)
    assert len(keys) == len(set(keys))
    assert all(_KEBAB.match(key) for key in keys)


def test_every_required_key_source_has_hint(tmp_path: Path) -> None:
    client = httpx.Client()
    sources = build_sources(client, HttpCache(tmp_path, client), UniversVersionMatcher(), "x")
    required = [
        s.descriptor
        for s in sources
        if s.descriptor.api_key_requirement == ApiKeyRequirement.REQUIRED
    ]
    assert {d.key for d in required} == {"snyk", "oss-index", "cvedetails"}
    assert all(d.api_key_hint for d in required)
