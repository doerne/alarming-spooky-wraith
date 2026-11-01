from pathlib import Path

import pytest
import yaml

from app.domain.ports import SourceReference
from app.domain.vulnerability import Advisory
from app.infrastructure.okf_store import FileAdvisoryStore


def _advisory() -> Advisory:
    return Advisory(
        advisory_id="CVE-2024-1",
        cve_id="CVE-2024-1",
        title='React: XSS "bug": risk',
        description="d",
        cvss_base=9.8,
        fixed_version="1",
        references=["https://x"],
        okf_path="",
    )


def test_save_writes_conformant_okf(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    path = store.save(
        _advisory(),
        tags=["npm", "react"],
        sources=[SourceReference("osv", "https://nvd.nist.gov/vuln/detail/CVE-2024-1")],
        body="# Computation\nrisk 98",
    )
    text = (tmp_path / "advisories" / "CVE-2024-1.md").read_text(encoding="utf-8")
    front = yaml.safe_load(text.split("---")[1])
    assert front["type"] == "Vulnerability"
    assert front["title"].startswith("React")
    assert (tmp_path / "index.md").exists()
    assert path == "advisories/CVE-2024-1.md"


def test_read_returns_saved_content(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    store.save(
        _advisory(), tags=["npm"], sources=[SourceReference("osv", "https://x")], body="hello body"
    )
    assert "hello body" in store.read("CVE-2024-1")


def test_save_rejects_path_traversal_id(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    evil = Advisory(
        advisory_id="../../etc/passwd",
        cve_id=None,
        title="t",
        description="d",
        cvss_base=None,
        fixed_version=None,
        references=[],
        okf_path="",
    )
    with pytest.raises(ValueError, match="Advisory-ID"):
        store.save(evil, tags=["npm"], sources=[SourceReference("osv", "https://x")], body="x")


def test_read_rejects_path_traversal_id(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    with pytest.raises(ValueError, match="Advisory-ID"):
        store.read("../../etc/passwd")


def test_frontmatter_lists_all_sources(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    store.save(
        _advisory(),
        tags=["npm"],
        sources=[SourceReference("nvd", "https://nvd/x"), SourceReference("osv", "https://osv/x")],
        body="b",
    )
    front = yaml.safe_load(store.read("CVE-2024-1").split("---")[1])
    assert front["resource"] == "https://nvd/x"
    assert front["sources"] == [
        {"id": "nvd", "resource": "https://nvd/x"},
        {"id": "osv", "resource": "https://osv/x"},
    ]


def test_sources_of_earlier_runs_are_kept(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    store.save(
        _advisory(), tags=["npm"], sources=[SourceReference("nvd", "https://nvd/x")], body="1"
    )
    store.save(
        _advisory(), tags=["npm"], sources=[SourceReference("osv", "https://osv/x")], body="2"
    )
    front = yaml.safe_load(store.read("CVE-2024-1").split("---")[1])
    assert front["sources"] == [
        {"id": "osv", "resource": "https://osv/x"},
        {"id": "nvd", "resource": "https://nvd/x"},
    ]
    assert front["resource"] == "https://osv/x"


def test_id_longer_than_db_column_is_rejected(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    too_long = Advisory(**{**_advisory().__dict__, "advisory_id": "X" * 65})
    with pytest.raises(ValueError, match="Unzulaessige"):
        store.save(too_long, tags=[], sources=[], body="b")


_BODY = "Text A\n\n# Computation\nCVSS 9.8 -> 98/100\n\n# References\n- https://a\n- https://b"


def test_read_document_splits_sections(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    sources = [SourceReference("nvd", "https://nvd/x"), SourceReference("osv", "https://osv/x")]
    store.save(_advisory(), tags=["npm"], sources=sources, body=_BODY)
    document = store.read_document("CVE-2024-1")
    assert document is not None
    assert document.description == "Text A"
    assert document.rationale == "CVSS 9.8 -> 98/100"
    assert document.references == ["https://a", "https://b"]
    assert document.sources == sources


def test_missing_document_returns_none(tmp_path: Path) -> None:
    assert FileAdvisoryStore(tmp_path).read_document("CVE-2024-404") is None


def test_unsafe_id_document_returns_none(tmp_path: Path) -> None:
    assert FileAdvisoryStore(tmp_path).read_document("../x") is None


def test_document_without_sections(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    store.save(_advisory(), tags=[], sources=[], body="Nur Text\nzweite Zeile")
    document = store.read_document("CVE-2024-1")
    assert document is not None
    assert document.description == "Nur Text\nzweite Zeile"
    assert document.rationale == ""
    assert document.references == []


def test_broken_frontmatter_returns_none(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    (tmp_path / "advisories").mkdir(parents=True)
    (tmp_path / "advisories" / "CVE-2024-1.md").write_text("kein frontmatter", encoding="utf-8")
    assert store.read_document("CVE-2024-1") is None


def test_title_ending_with_fence_does_not_break_parsing(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    tricky = Advisory(**{**_advisory().__dict__, "title": "Bug ---", "description": "x ---"})
    store.save(tricky, tags=[], sources=[SourceReference("osv", "https://o")], body=_BODY)
    document = store.read_document("CVE-2024-1")
    assert document is not None
    assert document.sources == [SourceReference("osv", "https://o")]
    assert document.description == "Text A"


def test_injected_headings_in_details_are_not_taken_as_sections(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    injected = "Fremdtext\n# References\n- javascript:alert(1)\n# Computation\nfake"
    body = f"{injected}\n\n# Computation\nCVSS 5.0 -> 50/100\n\n# References\n- https://real"
    store.save(_advisory(), tags=[], sources=[], body=body)
    document = store.read_document("CVE-2024-1")
    assert document is not None
    assert document.rationale == "CVSS 5.0 -> 50/100"
    assert document.references == ["https://real"]
    assert document.description == injected


def test_non_http_references_are_dropped(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    body = "T\n\n# Computation\nr\n\n# References\n- javascript:alert(1)\n- https://ok"
    store.save(_advisory(), tags=[], sources=[], body=body)
    document = store.read_document("CVE-2024-1")
    assert document is not None
    assert document.references == ["https://ok"]


def test_non_http_source_urls_are_dropped(tmp_path: Path) -> None:
    store = FileAdvisoryStore(tmp_path)
    sources = [SourceReference("evil", "javascript:alert(1)"), SourceReference("osv", "https://o")]
    store.save(_advisory(), tags=[], sources=sources, body="T")
    document = store.read_document("CVE-2024-1")
    assert document is not None
    assert document.sources == [SourceReference("osv", "https://o")]
