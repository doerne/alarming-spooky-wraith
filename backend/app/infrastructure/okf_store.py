"""Dateibasierter AdvisoryStore im Open Knowledge Format (OKF v0.2).

Jede Advisory ist ein eigenes Markdown-File mit YAML-Frontmatter; der Dateipfad
ist die Identitaet. Siehe docs/.../design.md und die OKF-SPEC v0.2.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.domain.vulnerability import Advisory

_INDEX = '---\nokf_version: "0.2"\n---\n\n# CVE-Radar Advisories\n'

# Erlaubte Advisory-IDs: keine Pfad-Trenner, kein '..'. Deckt CVE-/GHSA-/OSV-IDs.
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,99}$")


def _safe_id(advisory_id: str) -> str:
    if not _ID_RE.fullmatch(advisory_id):
        raise ValueError(f"Unzulaessige Advisory-ID: {advisory_id!r}")
    return advisory_id


class FileAdvisoryStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._dir = root / "advisories"

    def save(self, advisory: Advisory, *, tags: list[str], source_url: str, body: str) -> str:
        safe_id = _safe_id(advisory.advisory_id)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ensure_index()
        front = _frontmatter(advisory, tags=tags, source_url=source_url)
        yaml_block = yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
        content = f"---\n{yaml_block}---\n\n{body}\n"
        (self._dir / f"{safe_id}.md").write_text(content, encoding="utf-8")
        return f"advisories/{safe_id}.md"

    def read(self, advisory_id: str) -> str:
        safe_id = _safe_id(advisory_id)
        return (self._dir / f"{safe_id}.md").read_text(encoding="utf-8")

    def _ensure_index(self) -> None:
        index = self._root / "index.md"
        if not index.exists():
            index.write_text(_INDEX, encoding="utf-8")


def _frontmatter(advisory: Advisory, *, tags: list[str], source_url: str) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "type": "Vulnerability",
        "title": advisory.title,
        "description": advisory.description,
        "resource": source_url,
        "tags": tags,
        "timestamp": now,
        "sources": [{"id": "osv", "resource": source_url}],
        "generated": {"by": "process:cve-radar", "at": now},
    }
