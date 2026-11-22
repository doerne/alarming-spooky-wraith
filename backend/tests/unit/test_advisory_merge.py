from app.application.advisory_merge import (
    canonical_key,
    group_by_identity,
    identity_ids,
    merge_vulns,
)
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
    assert canonical_key(identity_ids(vuln)) == ("CVE-2024-9", "CVE-2024-9")


def test_cve_id_itself_is_cve() -> None:
    assert canonical_key(identity_ids(_vuln("nvd", id="CVE-2024-1"))) == (
        "CVE-2024-1",
        "CVE-2024-1",
    )


def test_canonical_prefers_cve_then_ghsa_then_min() -> None:
    assert canonical_key(["PYSEC-2026-1", "GHSA-zz", "CVE-2024-2", "CVE-2024-10"]) == (
        "CVE-2024-10",
        "CVE-2024-10",
    )
    assert canonical_key(["PYSEC-2026-4320", "GHSA-6q48-6c7w-9gw2"]) == (
        "GHSA-6q48-6c7w-9gw2",
        None,
    )
    assert canonical_key(["RUSTSEC-2024-2", "PYSEC-2024-1"]) == ("PYSEC-2024-1", None)


def test_groups_direct_aliases() -> None:
    ghsa = _vuln("osv", id="GHSA-6q48-6c7w-9gw2")
    pysec = _vuln("pypa", id="PYSEC-2026-4320", aliases=["GHSA-6q48-6c7w-9gw2"])
    assert group_by_identity([ghsa, pysec], identity_ids) == [[ghsa, pysec]]


def test_groups_transitively() -> None:
    first = _vuln("osv", id="A-1", aliases=["B-1"])
    third = _vuln("pypa", id="C-1")
    second = _vuln("ghsa", id="B-1", aliases=["C-1"])
    groups = group_by_identity([first, third, second], identity_ids)
    assert groups == [[first, third, second]]


def test_keeps_unrelated_apart() -> None:
    first = _vuln("osv", id="CVE-2024-1")
    second = _vuln("osv", id="CVE-2024-2")
    assert group_by_identity([first, second], identity_ids) == [[first], [second]]


def test_merge_lists_aliases_without_canonical() -> None:
    ghsa = _vuln("osv", id="GHSA-6q48-6c7w-9gw2")
    pysec = _vuln("pypa", id="PYSEC-2026-4320", aliases=["GHSA-6q48-6c7w-9gw2"])
    merged = merge_vulns([pysec, ghsa], _ORDER)
    assert merged.advisory_id == "GHSA-6q48-6c7w-9gw2"
    assert merged.cve_id is None
    assert merged.aliases == ("PYSEC-2026-4320",)


def test_zero_cvss_is_a_value() -> None:
    nvd = _vuln("nvd", cvss_base=0.0)
    osv = _vuln("osv", cvss_base=7.5)
    assert merge_vulns([osv, nvd], _ORDER).cvss_base == 0.0


def test_same_source_is_listed_once() -> None:
    merged = merge_vulns([_vuln("osv"), _vuln("osv")], _ORDER)
    assert merged.sources == [SourceReference("osv", "https://osv.example.org/CVE-2024-1")]


def test_invalid_aliases_are_ignored() -> None:
    too_long = "GHSA-" + "x" * 80
    vuln = _vuln("osv", id="PYSEC-2026-1", aliases=[too_long, "../etc/passwd", "GHSA-ok"])
    assert identity_ids(vuln) == frozenset({"PYSEC-2026-1", "GHSA-ok"})
    merged = merge_vulns([vuln], _ORDER)
    assert merged.advisory_id == "GHSA-ok"
    assert merged.aliases == ("PYSEC-2026-1",)


def test_invalid_own_id_falls_back_to_valid_alias() -> None:
    vuln = _vuln("osv", id="bad/id", aliases=["CVE-2026-7"])
    assert identity_ids(vuln) == frozenset({"CVE-2026-7"})
