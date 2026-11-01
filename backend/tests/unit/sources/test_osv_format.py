from app.domain.ports import AffectedPackage, RangeEvent
from app.infrastructure.sources.osv_format import parse_osv_record

_RECORD = {
    "id": "PYSEC-2024-1",
    "aliases": ["CVE-2024-5", "GHSA-q"],
    "summary": "SQL injection",
    "details": "long text",
    "affected": [
        {
            "package": {"ecosystem": "PyPI", "name": "django"},
            "ranges": [
                {
                    "type": "ECOSYSTEM",
                    "events": [{"introduced": "4.0"}, {"fixed": "4.2.11"}],
                }
            ],
            "versions": ["4.2.10"],
        }
    ],
    "references": [{"type": "WEB", "url": "https://example.org/advisory"}],
}


def test_parse_osv_affected_events() -> None:
    vuln = parse_osv_record(_RECORD, "pypa")
    assert vuln.source_key == "pypa"
    assert vuln.id == "PYSEC-2024-1"
    assert vuln.fixed_version == "4.2.11"
    assert vuln.affected == (
        AffectedPackage(
            ecosystem="PyPI",
            name="django",
            events=(RangeEvent("introduced", "4.0"), RangeEvent("fixed", "4.2.11")),
            versions=("4.2.10",),
        ),
    )


def test_url_defaults_to_first_reference_for_other_sources() -> None:
    assert parse_osv_record(_RECORD, "pypa").url == "https://example.org/advisory"


def test_explicit_url_wins() -> None:
    assert parse_osv_record(_RECORD, "pypa", url="https://x/y").url == "https://x/y"


def test_git_ranges_are_ignored() -> None:
    record = {
        "id": "X-1",
        "affected": [
            {
                "package": {"ecosystem": "Go", "name": "example.com/m"},
                "ranges": [{"type": "GIT", "events": [{"introduced": "abc123"}]}],
            }
        ],
    }
    assert parse_osv_record(record, "go-vulndb").affected[0].events == ()


def test_minimal_record() -> None:
    vuln = parse_osv_record({"id": "X-2"}, "osv")
    assert vuln.summary == ""
    assert vuln.cvss_base is None
    assert vuln.affected == ()
