"""Dateibasierter AdvisoryStore im Open Knowledge Format (OKF v0.2).

Jede Advisory ist ein eigenes Markdown-File mit YAML-Frontmatter; der Dateipfad
ist die Identitaet. Siehe docs/.../design.md und die OKF-SPEC v0.2.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.domain.ports import AdvisoryDocument, SourceReference
from app.domain.vulnerability import ADVISORY_ID_MAX_LENGTH, Advisory

_DOCUMENT = re.compile(r"\A---\n(.*?\n)---\n(.*)\Z", re.DOTALL)
_COMPUTATION_HEADING = "\n# Computation\n"
_REFERENCES_HEADING = "\n# References\n"
_HTTP_URL = re.compile(r"^https?://", re.IGNORECASE)
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

    def read_document(self, advisory_id: str) -> AdvisoryDocument | None:
        try:
            path = self._dir / f"{_safe_id(advisory_id)}.md"
        except ValueError:
            return None
        if not path.exists():
            return None
        split = _split_document(path.read_text(encoding="utf-8"))
        sources = _sources_from(split[0]) if split else None
        if split is None or sources is None:
            return None
        description, rationale, references = parse_okf_body(split[1])
        return AdvisoryDocument(description, rationale, references, sources)

    def _ensure_index(self) -> None:
        index = self._root / "index.md"
        if not index.exists():
            index.write_text(_INDEX, encoding="utf-8")


def _sources_from(frontmatter: str) -> list[SourceReference] | None:
    try:
        front = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(front, dict):
        return None
    entries = front.get("sources") or []
    references = [SourceReference(str(e.get("id")), str(e.get("resource"))) for e in entries]
    return [reference for reference in references if _HTTP_URL.match(reference.url)]


def _earlier_sources(path: Path) -> list[SourceReference]:
    if not path.exists():
        return []
    split = _split_document(path.read_text(encoding="utf-8"))
    return (_sources_from(split[0]) or []) if split else []


def _split_document(text: str) -> tuple[str, str] | None:
    """(Frontmatter, Body); die Fence muss eine eigene Zeile ``---`` sein."""
    match = _DOCUMENT.match(text)
    return (match.group(1), match.group(2)) if match else None


def parse_okf_body(body: str) -> tuple[str, str, list[str]]:
    """Body wie ``RunIngest`` ihn schreibt → (Beschreibung, Herleitung, Referenzen).

    Unsere Abschnitte stehen immer am Ende: deshalb an der *letzten* Überschrift
    teilen - Überschriften in Fremdtexten landen so in der Beschreibung.
    """
    text = f"\n{body}"
    head, found_references, references_part = text.rpartition(_REFERENCES_HEADING)
    if not found_references:
        head, references_part = text, ""
    description, found_computation, rationale = head.rpartition(_COMPUTATION_HEADING)
    if not found_computation:
        description, rationale = head, ""
    references = [
        line.strip()[2:].strip()
        for line in references_part.splitlines()
        if line.strip().startswith("- ")
    ]
    safe = [url for url in references if _HTTP_URL.match(url)]
    return description.strip(), rationale.strip(), safe


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
