"""RSS-/Atom-Feeds von Framework-Security-Seiten (Django, Spring).

Feeds nennen keine Versionsbereiche: Treffer entstehen nur über den Namen
(Scope NAME). Pro genannter CVE-ID entsteht ein Eintrag; Meldungen ohne
CVE-ID werden verworfen.
"""

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator

import httpx

from app.domain.errors import SourceAccessError
from app.domain.ports import AffectedPackage, SourceVuln
from app.domain.sources import MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.http_errors import send

_CVE = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)
_DOCTYPE = "<!DOCTYPE"
_SPRING_PROJECT = re.compile(
    r"\bSpring (Framework|Boot|Security|Data(?: \w+)?|Cloud(?: \w+)?|Integration|Batch|"
    r"AMQP|Kafka|Session|Shell|HATEOAS|GraphQL|Web Services|Authorization Server)\b"
)


def _parse(text: str) -> ET.Element:
    # Kein defusedxml im Projekt: Entity-Tricks gehen nur über DOCTYPE - daher abweisen.
    if _DOCTYPE.lower() in text.lower():
        raise SourceAccessError("Feed enthält eine DOCTYPE-Deklaration und wird abgewiesen")
    try:
        return ET.fromstring(text)
    except ET.ParseError as error:
        raise SourceAccessError("Antwort der Quelle ist kein gültiger Feed") from error


def _items(root: ET.Element) -> Iterator[tuple[str, str, str]]:
    """(Titel, Link, Text) je Eintrag; RSS ``item`` und Atom ``entry``."""
    atom = "{http://www.w3.org/2005/Atom}"
    for item in root.iter("item"):
        yield (item.findtext("title") or "", item.findtext("link") or "",
               item.findtext("description") or "")  # fmt: skip
    for entry in root.iter(f"{atom}entry"):
        link = entry.find(f"{atom}link")
        yield (entry.findtext(f"{atom}title") or "",
               link.get("href", "") if link is not None else "",
               entry.findtext(f"{atom}summary") or "")  # fmt: skip


def _cve_ids(*texts: str) -> list[str]:
    found = [match.upper() for text in texts for match in _CVE.findall(text)]
    return list(dict.fromkeys(found))


class _FeedSource:
    """Gemeinsamer Ablauf; Unterklassen liefern Descriptor, URL und Produktnamen."""

    descriptor: SourceDescriptor
    feed_url: str
    product_names: Callable[[str], tuple[str, ...]]

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def load(self, api_key: str | None, names: frozenset[str]) -> list[SourceVuln]:  # noqa: ARG002 - kein Key nötig
        if not names:
            return []
        root = _parse(send(self._client, "GET", self.feed_url).text)
        return [vuln for item in _items(root) for vuln in self._to_vulns(*item)]

    def _to_vulns(self, title: str, link: str, text: str) -> list[SourceVuln]:
        affected = tuple(AffectedPackage(None, name) for name in type(self).product_names(title))
        return [
            SourceVuln(
                source_key=self.descriptor.key,
                id=cve_id,
                aliases=[],
                summary=title,
                details="",
                cvss_base=None,
                fixed_version=None,
                references=[link] if link else [],
                url=link or self.descriptor.homepage_url,
                affected=affected,
            )
            for cve_id in _cve_ids(title, link, text)
        ]


def _django_names(_: str) -> tuple[str, ...]:
    return ("django",)


def _spring_names(title: str) -> tuple[str, ...]:
    projects = [
        f"spring-{project.lower().replace(' ', '-')}" for project in _SPRING_PROJECT.findall(title)
    ]
    return ("spring", *dict.fromkeys(projects))


class DjangoSource(_FeedSource):
    descriptor = SourceDescriptor(
        key="django",
        name="Django Security",
        homepage_url="https://www.djangoproject.com/weblog/",
        description="Security-Releases aus dem Django-Weblog; Treffer nur über den Namen "
        "„django“, ohne Versionsprüfung.",
        kind=SourceKind.BULK,
        scope=MatchScope.NAME,
    )
    feed_url = "https://www.djangoproject.com/rss/weblog/"
    product_names = staticmethod(_django_names)


class SpringSource(_FeedSource):
    descriptor = SourceDescriptor(
        key="spring",
        name="Spring Security Advisories",
        homepage_url="https://spring.io/security",
        description="Security-Advisories des Spring-Projekts; Treffer über „spring“ bzw. "
        "„spring-<projekt>“, ohne Versionsprüfung.",
        kind=SourceKind.BULK,
        scope=MatchScope.NAME,
    )
    feed_url = "https://spring.io/security.atom"
    product_names = staticmethod(_spring_names)
