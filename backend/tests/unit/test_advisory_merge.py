from app.application.advisory_merge import advisory_key, merge_vulns
from app.domain.ports import SourceReference, SourceVuln
from app.domain.sources import MERGE_PRECEDENCE

_ORDER = [*MERGE_PRECEDENCE, "rustsec"]


def _vuln(source_key: str, **overrides: object) -> SourceVuln:
    values: dict[str, object] = {
        "source_key": source_key,
        "id": "CVE-2024-1",
        "aliases": [],
        "summary": f"summary {source_key}",
        "details": "",
        "cvss_base": None,
        "fixed_version": None,
        "references": [],
        "url": f"https://{source_key}.example.org/CVE-2024-1",
    }
    values.update(overrides)
    return SourceVuln(**values)  # type: ignore[arg-type]


def test_nvd_cvss_wins_over_osv() -> None:
    osv = _vuln("osv", cvss_base=7.5)
    nvd = _vuln("nvd", cvss_base=9.8)
    assert merge_vulns([osv, nvd], _ORDER).cvss_base == 9.8
    assert merge_vulns([nvd, osv], _ORDER).cvss_base == 9.8


def test_lower_rank_fills_missing_value() -> None:
    nvd = _vuln("nvd", cvss_base=9.8)
    osv = _vuln("osv", fixed_version="1.2.3")
    merged = merge_vulns([osv, nvd], _ORDER)
    assert merged.fixed_version == "1.2.3"
    assert merged.title == "summary nvd"


def test_unknown_source_ranks_last() -> None:
    other = _vuln("django", cvss_base=5.0)
    rustsec = _vuln("rustsec", cvss_base=6.0)
    assert merge_vulns([other, rustsec], _ORDER).cvss_base == 6.0


def test_references_are_unioned() -> None:
    osv = _vuln("osv", references=["https://a", "https://b"])
    nvd = _vuln("nvd", references=["https://b", "https://c"])
    merged = merge_vulns([osv, nvd], _ORDER)
    assert merged.references == ["https://b", "https://c", "https://a"]
    assert merged.sources == [
        SourceReference("nvd", "https://nvd.example.org/CVE-2024-1"),
        SourceReference("osv", "https://osv.example.org/CVE-2024-1"),
    ]


def test_cve_alias_becomes_id() -> None:
    vuln = _vuln("osv", id="GHSA-aaaa", aliases=["GHSA-bbbb", "CVE-2024-9"])
    assert advisory_key(vuln) == ("CVE-2024-9", "CVE-2024-9")


def test_cve_id_itself_is_cve() -> None:
    assert advisory_key(_vuln("nvd", id="CVE-2024-1")) == ("CVE-2024-1", "CVE-2024-1")


def test_ghsa_without_cve_keeps_id() -> None:
    assert advisory_key(_vuln("ghsa", id="GHSA-abcd")) == ("GHSA-abcd", None)


def test_zero_cvss_is_a_value() -> None:
    nvd = _vuln("nvd", cvss_base=0.0)
    osv = _vuln("osv", cvss_base=7.5)
    assert merge_vulns([osv, nvd], _ORDER).cvss_base == 0.0


def test_same_source_is_listed_once() -> None:
    merged = merge_vulns([_vuln("osv"), _vuln("osv")], _ORDER)
    assert merged.sources == [SourceReference("osv", "https://osv.example.org/CVE-2024-1")]
