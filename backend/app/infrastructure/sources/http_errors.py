"""Einheitliche HTTP-Aufrufe für Quellen: Fehler werden zu SourceAccessError."""

from typing import Any

import httpx

from app.domain.errors import SourceAccessError

_STATUS_MESSAGES = {
    401: "Zugriff verweigert - API-Key prüfen",
    403: "Zugriff verweigert - API-Key prüfen",
    429: "Rate-Limit der Quelle erreicht - später erneut versuchen",
}
_SERVER_ERROR = 500
_UNREACHABLE = "Quelle nicht erreichbar"


def ensure_ok(response: httpx.Response) -> None:
    status = response.status_code
    if status < httpx.codes.BAD_REQUEST:
        return
    if status in _STATUS_MESSAGES:
        raise SourceAccessError(_STATUS_MESSAGES[status])
    if status >= _SERVER_ERROR:
        raise SourceAccessError(f"{_UNREACHABLE} (HTTP {status})")
    raise SourceAccessError(f"Anfrage abgelehnt (HTTP {status})")


def send(client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    try:
        response = client.request(method, url, **kwargs)
    except httpx.HTTPError as error:
        raise SourceAccessError(f"{_UNREACHABLE}: {error}") from error
    ensure_ok(response)
    return response


def get_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    not_found_is_empty: bool = False,
    **kwargs: Any,
) -> Any:
    """JSON-Antwort; mit ``not_found_is_empty`` ergibt HTTP 404 ``None``."""
    try:
        response = client.request(method, url, **kwargs)
    except httpx.HTTPError as error:
        raise SourceAccessError(f"{_UNREACHABLE}: {error}") from error
    if not_found_is_empty and response.status_code == httpx.codes.NOT_FOUND:
        return None
    ensure_ok(response)
    try:
        return response.json()
    except ValueError as error:
        raise SourceAccessError("Antwort der Quelle ist kein gültiges JSON") from error
