from pathlib import Path

import yaml

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
        source_url="https://nvd.nist.gov/vuln/detail/CVE-2024-1",
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
    store.save(_advisory(), tags=["npm"], source_url="https://x", body="hello body")
    assert "hello body" in store.read("CVE-2024-1")
