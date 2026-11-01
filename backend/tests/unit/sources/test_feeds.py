import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.domain.ports import AffectedPackage
from app.infrastructure.sources.feeds import DjangoSource, SpringSource
from tests.unit.sources.helpers import mock_client, status_client

_DJANGO_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>Django</title>
<item><title>Django security releases issued: 5.1.2 and 4.2.17</title>
<link>https://www.djangoproject.com/weblog/2026/oct/01/security-releases/</link>
<description>Fixes CVE-2026-1001 and CVE-2026-1002 in the ORM.</description></item>
<item><title>Django 6.0 released</title>
<link>https://www.djangoproject.com/weblog/2026/sep/01/django-60/</link>
<description>New features.</description></item>
</channel></rss>"""

_SPRING_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Spring Security Advisories</title>
<item><title>cve-2026-47834 - MEDIUM - Spring Data JPA Sort expression validation bypass</title>
<link>https://spring.io/security/cve-2026-47834</link>
<description>Bypass.</description></item>
</channel></rss>"""


def _client(body: str) -> httpx.Client:
    return mock_client(lambda _: httpx.Response(200, text=body))


def test_django_maps_record() -> None:
    vulns = DjangoSource(_client(_DJANGO_RSS)).load(None, frozenset({"django"}))
    assert [vuln.id for vuln in vulns] == ["CVE-2026-1001", "CVE-2026-1002"]
    vuln = vulns[0]
    assert vuln.summary == "Django security releases issued: 5.1.2 and 4.2.17"
    assert vuln.url == "https://www.djangoproject.com/weblog/2026/oct/01/security-releases/"
    assert vuln.affected == (AffectedPackage(None, "django"),)


def test_django_entry_without_cve_is_dropped() -> None:
    body = _DJANGO_RSS.replace("CVE-2026-1001 and CVE-2026-1002", "nothing")
    assert DjangoSource(_client(body)).load(None, frozenset({"django"})) == []


def test_spring_maps_record() -> None:
    vulns = SpringSource(_client(_SPRING_RSS)).load(None, frozenset({"spring"}))
    vuln = vulns[0]
    assert vuln.id == "CVE-2026-47834"
    assert vuln.url == "https://spring.io/security/cve-2026-47834"
    assert vuln.affected == (
        AffectedPackage(None, "spring"),
        AffectedPackage(None, "spring-data-jpa"),
    )


def test_spring_entry_without_cve_is_dropped() -> None:
    body = _SPRING_RSS.replace("cve-2026-47834 - MEDIUM - ", "").replace("/cve-2026-47834", "/x")
    assert SpringSource(_client(body)).load(None, frozenset({"spring"})) == []


def test_feed_without_names_does_not_download() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("darf nicht laden")

    assert DjangoSource(mock_client(handler)).load(None, frozenset()) == []


def test_feed_with_doctype_is_rejected() -> None:
    body = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><rss><channel/></rss>'
    with pytest.raises(SourceAccessError, match="DOCTYPE"):
        DjangoSource(_client(body)).load(None, frozenset({"django"}))


def test_broken_feed_is_rejected() -> None:
    with pytest.raises(SourceAccessError, match="kein gültiger Feed"):
        DjangoSource(_client("<rss><channel>")).load(None, frozenset({"django"}))


def test_feed_http_error_raises_source_access_error() -> None:
    with pytest.raises(SourceAccessError, match="nicht erreichbar"):
        SpringSource(status_client(503)).load(None, frozenset({"spring"}))
