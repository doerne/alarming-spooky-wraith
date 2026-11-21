"""Adapter zur GitHub App: legt Issues an und liest bzw. schreibt ihren Zustand (httpx).

Der private Schlüssel wird nur hier gelesen und nie geloggt oder in Meldungen ausgegeben.
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt

from app.domain.errors import IssueTrackerError
from app.domain.issues import ISSUE_LABEL, find_markers
from app.domain.ports import IssueContent, TrackedIssue
from app.infrastructure.config import Settings

_API_VERSION = "2022-11-28"
_JWT_BACKDATE = timedelta(seconds=60)
_JWT_LIFETIME = timedelta(minutes=9)
_TOKEN_RENEW_MARGIN = timedelta(minutes=5)
_PAGE_SIZE = 100
_CREATE_PAUSE_SECONDS = 1.0
_LABEL_EXISTS_STATUS = 422
_BAD_REQUEST_STATUS = 400
_UNAUTHORIZED_STATUS = 401
_FORBIDDEN_STATUS = 403
_NOT_FOUND_STATUS = 404
_TOO_MANY_REQUESTS_STATUS = 429
_RATE_LIMIT_HEADER = "x-ratelimit-remaining"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _to_tracked(item: dict[str, Any]) -> TrackedIssue:
    return TrackedIssue(
        number=int(item["number"]),
        url=str(item["html_url"]),
        is_open=item["state"] == "open",
        not_planned=item.get("state_reason") == "not_planned",
    )


def _error_message(response: httpx.Response) -> str:
    status = response.status_code
    if status == _UNAUTHORIZED_STATUS:
        return "GitHub lehnt die Anmeldung ab (App-ID oder Schlüssel prüfen)"
    if _is_rate_limited(response):
        return "GitHub-Rate-Limit erreicht, später erneut versuchen"
    if status == _FORBIDDEN_STATUS:
        return "Zugriff verweigert (Berechtigungen der GitHub App prüfen)"
    if status == _NOT_FOUND_STATUS:
        return "Repository nicht gefunden oder die GitHub App ist dort nicht installiert"
    return f"GitHub-Fehler (HTTP {status})"


def _is_rate_limited(response: httpx.Response) -> bool:
    if response.status_code == _TOO_MANY_REQUESTS_STATUS:
        return True
    return (
        response.status_code == _FORBIDDEN_STATUS
        and response.headers.get(_RATE_LIMIT_HEADER) == "0"
    )


class GitHubAppIssueTracker:
    """Implementiert den Port ``IssueTracker`` über die REST-API von GitHub."""

    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], datetime] = _utc_now,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._client = httpx.Client(
            base_url=settings.github_api_url, transport=transport, timeout=30.0
        )
        self._clock = clock
        self._sleep = sleep
        self._installation_ids: dict[str, int] = {}
        self._tokens: dict[int, tuple[str, datetime]] = {}
        self._known_labels: dict[str, set[str]] = {}
        self._created_once = False

    def is_configured(self) -> bool:
        return bool(self._settings.github_app_id) and bool(self._read_key())

    def existing_markers(self, repository: str) -> dict[str, TrackedIssue]:
        markers: dict[str, TrackedIssue] = {}
        url: str | None = (
            f"/repos/{repository}/issues?labels={ISSUE_LABEL}&state=all&per_page={_PAGE_SIZE}"
        )
        while url:
            response = self._authorized(repository, "GET", url)
            for item in response.json():
                if "pull_request" not in item:
                    self._index_markers(item, markers)
            url = response.links.get("next", {}).get("url")
        return markers

    def get(self, repository: str, number: int) -> TrackedIssue | None:
        response = self._authorized(
            repository,
            "GET",
            f"/repos/{repository}/issues/{number}",
            allowed=(_NOT_FOUND_STATUS,),
        )
        if response.status_code == _NOT_FOUND_STATUS:
            return None
        return _to_tracked(response.json())

    def create(self, repository: str, content: IssueContent) -> TrackedIssue:
        self._ensure_labels(repository, content.labels)
        if self._created_once:
            self._sleep(_CREATE_PAUSE_SECONDS)
        response = self._authorized(
            repository,
            "POST",
            f"/repos/{repository}/issues",
            json={"title": content.title, "body": content.body, "labels": list(content.labels)},
        )
        self._created_once = True
        return _to_tracked(response.json())

    def set_open(
        self, repository: str, number: int, is_open: bool, comment: str, not_planned: bool = False
    ) -> None:
        base = f"/repos/{repository}/issues/{number}"
        self._authorized(repository, "POST", f"{base}/comments", json={"body": comment})
        self._authorized(
            repository,
            "PATCH",
            base,
            json={
                "state": "open" if is_open else "closed",
                "state_reason": _reason(is_open, not_planned),
            },
        )

    # --- Hilfen -------------------------------------------------------------

    def _read_key(self) -> str:
        try:
            return self._settings.github_app_private_key_file.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def _private_key(self) -> str:
        key = self._read_key()
        if not key or not self._settings.github_app_id:
            raise IssueTrackerError("GitHub ist nicht konfiguriert")
        return key

    def _app_jwt(self) -> str:
        now = self._clock()
        claims = {
            "iat": int((now - _JWT_BACKDATE).timestamp()),
            "exp": int((now + _JWT_LIFETIME).timestamp()),
            "iss": self._settings.github_app_id,
        }
        return jwt.encode(claims, self._private_key(), algorithm="RS256")

    def _send(
        self,
        method: str,
        url: str,
        token: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": _API_VERSION,
        }
        try:
            return self._client.request(method, url, json=json, headers=headers)
        except httpx.HTTPError as error:
            raise IssueTrackerError("GitHub ist nicht erreichbar") from error

    @staticmethod
    def _check(response: httpx.Response, allowed: tuple[int, ...] = ()) -> None:
        if response.status_code < _BAD_REQUEST_STATUS or response.status_code in allowed:
            return
        raise IssueTrackerError(_error_message(response))

    def _authorized(
        self,
        repository: str,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        allowed: tuple[int, ...] = (),
    ) -> httpx.Response:
        response = self._send(method, url, self._installation_token(repository), json=json)
        self._check(response, allowed)
        return response

    def _installation_token(self, repository: str) -> str:
        installation_id = self._installation_id(repository)
        now = self._clock()
        cached = self._tokens.get(installation_id)
        if cached and cached[1] - _TOKEN_RENEW_MARGIN > now:
            return cached[0]
        response = self._send(
            "POST", f"/app/installations/{installation_id}/access_tokens", self._app_jwt()
        )
        self._check(response)
        body = response.json()
        expires_at = datetime.fromisoformat(str(body["expires_at"]))
        self._tokens[installation_id] = (str(body["token"]), expires_at)
        return str(body["token"])

    def _installation_id(self, repository: str) -> int:
        if repository not in self._installation_ids:
            response = self._send("GET", f"/repos/{repository}/installation", self._app_jwt())
            self._check(response)
            self._installation_ids[repository] = int(response.json()["id"])
        return self._installation_ids[repository]

    def _ensure_labels(self, repository: str, labels: tuple[str, ...]) -> None:
        known = self._known_labels.setdefault(repository, set())
        for label in labels:
            if label not in known:
                self._authorized(
                    repository,
                    "POST",
                    f"/repos/{repository}/labels",
                    json={"name": label},
                    allowed=(_LABEL_EXISTS_STATUS,),
                )
                known.add(label)

    @staticmethod
    def _index_markers(item: dict[str, Any], markers: dict[str, TrackedIssue]) -> None:
        tracked = _to_tracked(item)
        for marker in find_markers(str(item.get("body") or "")):
            markers[marker] = tracked


def _reason(is_open: bool, not_planned: bool) -> str:
    if is_open:
        return "reopened"
    return "not_planned" if not_planned else "completed"
