from pathlib import Path

import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.infrastructure.sources.http_cache import HttpCache
from app.infrastructure.sources.http_errors import get_json

_URL = "https://example.org/dump.zip"


def test_cache_sends_etag_and_reuses_file_on_304(tmp_path: Path) -> None:
    seen_headers: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers.get("If-None-Match"))
        if request.headers.get("If-None-Match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, content=b"payload", headers={"ETag": '"v1"'})

    cache = HttpCache(tmp_path, httpx.Client(transport=httpx.MockTransport(handler)))
    first = cache.fetch("demo", _URL)
    second = cache.fetch("demo", _URL)
    assert first == second
    assert second.read_bytes() == b"payload"
    assert seen_headers == [None, '"v1"']


def test_cache_replaces_file_when_changed(tmp_path: Path) -> None:
    bodies = iter([b"old", b"new"])

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=next(bodies))

    cache = HttpCache(tmp_path, httpx.Client(transport=httpx.MockTransport(handler)))
    cache.fetch("demo", _URL)
    assert cache.fetch("demo", _URL).read_bytes() == b"new"


def test_cache_error_raises_source_access_error(tmp_path: Path) -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
    with pytest.raises(SourceAccessError, match="nicht erreichbar"):
        HttpCache(tmp_path, client).fetch("demo", _URL)


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "API-Key"),
        (403, "API-Key"),
        (429, "Rate-Limit"),
        (500, "nicht erreichbar"),
        (404, "HTTP 404"),
    ],
)
def test_get_json_maps_http_errors(status: int, message: str) -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status)))
    with pytest.raises(SourceAccessError, match=message):
        get_json(client, "GET", _URL)


def test_get_json_maps_connection_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(SourceAccessError, match="nicht erreichbar"):
        get_json(client, "GET", _URL)


def test_get_json_rejects_non_json() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="<html>"))
    )
    with pytest.raises(SourceAccessError, match="kein gültiges JSON"):
        get_json(client, "GET", _URL)
