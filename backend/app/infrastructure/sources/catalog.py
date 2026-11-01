"""Katalog aller eingebauten Quellen. Neue Quelle = neues Modul + Eintrag hier.

Die Reihenfolge ist die Anzeige-Reihenfolge der Quellen-Seite.
"""

import httpx

from app.domain.ports import VersionMatcher, VulnerabilitySource
from app.infrastructure.sources.cve_org import CveOrgSource
from app.infrastructure.sources.cvedetails import CvedetailsSource
from app.infrastructure.sources.euvd import EuvdSource
from app.infrastructure.sources.feeds import DjangoSource, SpringSource
from app.infrastructure.sources.ghsa import GhsaSource
from app.infrastructure.sources.http_cache import HttpCache
from app.infrastructure.sources.nodejs import NodejsSource
from app.infrastructure.sources.nvd import NvdSource
from app.infrastructure.sources.oss_index import OssIndexSource
from app.infrastructure.sources.osv import OsvSource
from app.infrastructure.sources.osv_dumps import OSV_DUMP_DESCRIPTORS, OsvDumpSource
from app.infrastructure.sources.packagist import PackagistSource
from app.infrastructure.sources.repo_advisories import LaravelSource, SymfonySource
from app.infrastructure.sources.rubysec import RubysecSource
from app.infrastructure.sources.snyk import SnykSource


def build_sources(
    client: httpx.Client, cache: HttpCache, versions: VersionMatcher, osv_base_url: str
) -> list[VulnerabilitySource]:
    dumps = {
        key: OsvDumpSource(descriptor, cache) for key, descriptor in OSV_DUMP_DESCRIPTORS.items()
    }
    return [
        # Übergreifende Datenbanken
        OsvSource(osv_base_url, client),
        GhsaSource(client),
        NvdSource(client),
        EuvdSource(client),
        CveOrgSource(client, cache),
        CvedetailsSource(client),
        SnykSource(client),
        OssIndexSource(client),
        # Sprachspezifische Datenbanken
        dumps["pypa"],
        dumps["go-vulndb"],
        dumps["rustsec"],
        RubysecSource(cache),
        PackagistSource(client, versions),
        dumps["haskell"],
        dumps["rconsortium"],
        dumps["opam"],
        # Framework-Security-Seiten
        DjangoSource(client),
        SpringSource(client),
        NodejsSource(client),
        SymfonySource(client),
        LaravelSource(client),
    ]
