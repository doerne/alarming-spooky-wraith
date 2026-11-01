"""Datei-Cache für große Abzüge (Repo-Zips, Feeds) mit ETag/Last-Modified.

Ein unveränderter Abzug wird nicht erneut geladen (HTTP 304).
"""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

import httpx

from app.domain.errors import SourceAccessError
from app.infrastructure.sources.http_errors import ensure_ok

_NOT_MODIFIED = 304
_CHUNK_SIZE = 1024 * 1024


class HttpCache:
    def __init__(self, root: Path, client: httpx.Client) -> None:
        self._root = root
        self._client = client

    def fetch(self, source_key: str, url: str, headers: Mapping[str, str] | None = None) -> Path:
        target = self._path(source_key, url)
        meta_path = target.with_suffix(".meta.json")
        meta = _read_meta(meta_path) if target.exists() else {}
        request_headers = {**(headers or {}), **_conditional_headers(meta)}
        try:
            with self._client.stream("GET", url, headers=request_headers) as response:
                if response.status_code == _NOT_MODIFIED and target.exists():
                    return target
                ensure_ok(response)
                _download(response, target)
                _write_meta(meta_path, response.headers)
        except httpx.HTTPError as error:
            raise SourceAccessError(f"Quelle nicht erreichbar: {error}") from error
        return target

    def _path(self, source_key: str, url: str) -> Path:
        digest = hashlib.sha256(url.encode()).hexdigest()[:16]
        folder = self._root / source_key
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{digest}.data"


def _conditional_headers(meta: Mapping[str, str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    if "etag" in meta:
        headers["If-None-Match"] = meta["etag"]
    if "last_modified" in meta:
        headers["If-Modified-Since"] = meta["last_modified"]
    return headers


def _download(response: httpx.Response, target: Path) -> None:
    partial = target.with_suffix(".part")
    with partial.open("wb") as file:
        for chunk in response.iter_bytes(_CHUNK_SIZE):
            file.write(chunk)
    partial.replace(target)


def _read_meta(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {key: str(value) for key, value in data.items()}


def _write_meta(path: Path, headers: httpx.Headers) -> None:
    meta = {"etag": headers.get("ETag"), "last_modified": headers.get("Last-Modified")}
    path.write_text(json.dumps({k: v for k, v in meta.items() if v}), encoding="utf-8")
