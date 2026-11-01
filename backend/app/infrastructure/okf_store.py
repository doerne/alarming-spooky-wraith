"""Dateibasierter AdvisoryStore im Open Knowledge Format (OKF v0.2).

Jede Advisory ist ein eigenes Markdown-File mit YAML-Frontmatter; der Dateipfad
ist die Identitaet. Siehe docs/.../design.md und die OKF-SPEC v0.2.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.domain.ports import SourceReference
from app.domain.vulnerability import ADVISORY_ID_MAX_LENGTH, Advisory

_INDEX = '---\nokf_version: "0.2"\n---\n\n# CVE-Radar Advisories\n'

# Erlaubte Advisory-IDs: keine Pfad-Trenner, kein '..'. Deckt CVE-/GHSA-/OSV-IDs.
_ID_RE = re.compile(rf"^[A-Za-z0-9][A-Za-z0-9_-]{{1,{ADVISORY_ID_MAX_LENGTH - 1}}}$")


def _safe_id(advisory_id: str) -> str:
    if not _ID_RE.fullmatch(advisory_id):
        raise ValueError(f"Unzulaessige Advisory-ID: {advisory_id!r}")
    return advisory_id


class FileAdvisoryStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._dir = root / "advisories"

    def save(
        self, advisory: Advisory, *, tags: list[str], sources: list[SourceReference], body: str
    ) -> str:
        safe_id = _safe_id(advisory.advisory_id)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ensure_index()
        path = self._dir / f"{safe_id}.md"
        front = _frontmatter(advisory, tags=tags, sources=_with_earlier(path, sources))
        yaml_block = yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
        content = f"---\n{yaml_block}---\n\n{body}\n"
        path.write_text(content, encoding="utf-8")
        return f"advisories/{safe_id}.md"

    def read(self, advisory_id: str) -> str:
        safe_id = _safe_id(advisory_id)
        return (self._dir / f"{safe_id}.md").read_text(encoding="utf-8")

    def _ensure_index(self) -> None:
        index = self._root / "index.md"
        if not index.exists():
            index.write_text(_INDEX, encoding="utf-8")


def _earlier_sources(path: Path) -> list[SourceReference]:
    if not path.exists():
        return []
    try:
        front = yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1]) or {}
    except (IndexError, yaml.YAMLError):
        return []
    entries = front.get("sources") or []
    return [SourceReference(str(e.get("id")), str(e.get("resource"))) for e in entries]


def _with_earlier(path: Path, sources: list[SourceReference]) -> list[SourceReference]:
    """Quellen früherer Läufe bleiben belegt (Spec §7); die aktuellen stehen vorn."""
    current = {source.source_key for source in sources}
    earlier = [s for s in _earlier_sources(path) if s.source_key not in current]
    return [*sources, *earlier]


def _frontmatter(
    advisory: Advisory, *, tags: list[str], sources: list[SourceReference]
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "type": "Vulnerability",
        "title": advisory.title,
        "description": advisory.description,
        "resource": sources[0].url if sources else "",
        "tags": tags,
        "timestamp": now,
        "sources": [{"id": source.source_key, "resource": source.url} for source in sources],
        "generated": {"by": "process:cve-radar", "at": now},
    }
