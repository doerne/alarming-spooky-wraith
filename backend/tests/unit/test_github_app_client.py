import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.domain.errors import IssueTrackerError
from app.domain.ports import IssueContent
from app.infrastructure.config import Settings
from app.infrastructure.github.app_client import GitHubAppIssueTracker

REPO = "acme/shop"
API = "https://api.example"
NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def key_pair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return private, public


class Api:
    """Scripted GitHub: Antworten je Methode+Pfad, Protokoll aller Anfragen."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.routes: dict[tuple[str, str], list[httpx.Response]] = {}

    def on(self, method: str, path: str, *responses: httpx.Response) -> None:
        self.routes[(method, path)] = list(responses)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = (request.method, request.url.path)
        queue = self.routes.get(key)
        if not queue:
            return httpx.Response(500, json={"message": f"unrouted {key}"})
        return queue.pop(0) if len(queue) > 1 else queue[0]

    def calls(self, method: str, path: str) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == method and r.url.path == path]


def _json(
    payload: object, status: int = 200, headers: dict[str, str] | None = None
) -> httpx.Response:
    return httpx.Response(status, json=payload, headers=headers)


def _installation_routes(api: Api) -> None:
    api.on("GET", "/repos/acme/shop/installation", _json({"id": 99}))
    api.on(
        "POST",
        "/app/installations/99/access_tokens",
        _json({"token": "ghs_secret", "expires_at": "2099-01-01T00:00:00Z"}),
    )


@pytest.fixture
def key_file(tmp_path: Path, key_pair: tuple[str, str]) -> Path:
    path = tmp_path / "key.pem"
    path.write_text(key_pair[0], encoding="utf-8")
    return path


def _tracker(api: Api, key_file: Path, sleeps: list[float] | None = None) -> GitHubAppIssueTracker:
    settings = Settings(
        github_app_id="123", github_app_private_key_file=key_file, github_api_url=API
    )
    return GitHubAppIssueTracker(
        settings,
        transport=httpx.MockTransport(api.handle),
        clock=lambda: NOW,
        sleep=(sleeps if sleeps is not None else []).append,
    )


def test_is_not_configured_without_app_id_or_key(tmp_path: Path) -> None:
    empty = tmp_path / "empty.pem"
    empty.write_text("", encoding="utf-8")
    no_id = Settings(github_app_id=None, github_app_private_key_file=empty, github_api_url=API)
    assert GitHubAppIssueTracker(no_id, clock=lambda: NOW).is_configured() is False
    no_key = Settings(github_app_id="123", github_app_private_key_file=empty, github_api_url=API)
    assert GitHubAppIssueTracker(no_key, clock=lambda: NOW).is_configured() is False


def test_app_jwt_is_rs256_with_issuer_and_one_minute_back_dating(
    key_file: Path, key_pair: tuple[str, str]
) -> None:
    api = Api()
    _installation_routes(api)
    api.on(
        "GET", "/repos/acme/shop/issues/7", _json({"number": 7, "html_url": "u", "state": "open"})
    )

    _tracker(api, key_file).get(REPO, 7)

    app_token = api.calls("GET", "/repos/acme/shop/installation")[0].headers["Authorization"]
    claims = jwt.decode(
        app_token.removeprefix("Bearer "),
        key_pair[1],
        algorithms=["RS256"],
        options={"verify_exp": False},
    )
    assert claims["iss"] == "123"
    assert claims["iat"] == int(NOW.timestamp()) - 60
    assert claims["exp"] == int(NOW.timestamp()) + 540


def test_installation_token_is_cached_between_calls(key_file: Path) -> None:
    api = Api()
    _installation_routes(api)
    api.on(
        "GET", "/repos/acme/shop/issues/7", _json({"number": 7, "html_url": "u", "state": "open"})
    )
    tracker = _tracker(api, key_file)

    tracker.get(REPO, 7)
    tracker.get(REPO, 7)

    assert len(api.calls("POST", "/app/installations/99/access_tokens")) == 1


def test_existing_markers_follow_pagination_and_skip_pull_requests(key_file: Path) -> None:
    marker_a = "<!-- cve-radar:application=1;advisory=CVE-1 -->"
    marker_b = "<!-- cve-radar:application=1;advisory=CVE-2 -->"
    api = Api()
    _installation_routes(api)
    next_page = f"{API}/repos/acme/shop/issues?labels=security&state=all&per_page=100&page=2"
    api.on(
        "GET",
        "/repos/acme/shop/issues",
        _json(
            [
                {"number": 1, "html_url": "u1", "state": "open", "body": f"x\n{marker_a}"},
                {"number": 2, "html_url": "u2", "state": "open", "body": "", "pull_request": {}},
            ],
            headers={"Link": f'<{next_page}>; rel="next"'},
        ),
        _json([{"number": 3, "html_url": "u3", "state": "closed", "body": marker_b}]),
    )

    markers = _tracker(api, key_file).existing_markers(REPO)

    assert set(markers) == {marker_a, marker_b}
    assert markers[marker_a].number == 1
    assert markers[marker_b].is_open is False


def test_create_adds_missing_labels_ignoring_exists_and_pauses_between_creations(
    key_file: Path,
) -> None:
    api = Api()
    _installation_routes(api)
    api.on("POST", "/repos/acme/shop/labels", _json({"message": "already_exists"}, status=422))
    api.on(
        "POST",
        "/repos/acme/shop/issues",
        _json({"number": 5, "html_url": "u5", "state": "open"}, status=201),
        _json({"number": 6, "html_url": "u6", "state": "open"}, status=201),
    )
    sleeps: list[float] = []
    tracker = _tracker(api, key_file, sleeps)
    content = IssueContent(title="t", body="b", labels=("security", "risk:hoch"), marker="m")

    first = tracker.create(REPO, content)
    tracker.create(REPO, content)

    assert first.number == 5
    assert len(api.calls("POST", "/repos/acme/shop/labels")) == 2
    body = json.loads(api.calls("POST", "/repos/acme/shop/issues")[0].content)
    assert body == {"title": "t", "body": "b", "labels": ["security", "risk:hoch"]}
    assert sleeps == [1.0]


def test_set_open_posts_comment_then_closes_as_completed(key_file: Path) -> None:
    api = Api()
    _installation_routes(api)
    api.on("POST", "/repos/acme/shop/issues/7/comments", _json({}, status=201))
    api.on(
        "PATCH",
        "/repos/acme/shop/issues/7",
        _json({"number": 7, "html_url": "u", "state": "closed"}),
    )

    _tracker(api, key_file).set_open(REPO, 7, False, "Behoben: x")

    assert [
        r.method
        for r in api.requests
        if r.url.path.endswith("/7/comments") or r.url.path.endswith("/issues/7")
    ] == ["POST", "PATCH"]
    patch = json.loads(api.calls("PATCH", "/repos/acme/shop/issues/7")[0].content)
    assert patch == {"state": "closed", "state_reason": "completed"}


def test_set_open_with_not_planned_uses_that_reason(key_file: Path) -> None:
    api = Api()
    _installation_routes(api)
    api.on("POST", "/repos/acme/shop/issues/7/comments", _json({}, status=201))
    api.on(
        "PATCH",
        "/repos/acme/shop/issues/7",
        _json({"number": 7, "html_url": "u", "state": "closed"}),
    )

    _tracker(api, key_file).set_open(REPO, 7, False, "x", True)

    patch = json.loads(api.calls("PATCH", "/repos/acme/shop/issues/7")[0].content)
    assert patch["state_reason"] == "not_planned"


def test_get_returns_none_for_missing_issue(key_file: Path) -> None:
    api = Api()
    _installation_routes(api)
    api.on("GET", "/repos/acme/shop/issues/7", _json({"message": "Not Found"}, status=404))

    assert _tracker(api, key_file).get(REPO, 7) is None


@pytest.mark.parametrize(
    ("status", "headers", "fragment"),
    [
        (401, {}, "Anmeldung"),
        (403, {}, "Zugriff verweigert"),
        (403, {"x-ratelimit-remaining": "0"}, "Rate-Limit"),
        (429, {}, "Rate-Limit"),
    ],
)
def test_error_statuses_become_readable_domain_errors_without_token(
    key_file: Path, status: int, headers: dict[str, str], fragment: str
) -> None:
    api = Api()
    _installation_routes(api)
    api.on(
        "GET", "/repos/acme/shop/issues/7", _json({"message": "x"}, status=status, headers=headers)
    )

    with pytest.raises(IssueTrackerError) as raised:
        _tracker(api, key_file).get(REPO, 7)

    assert fragment in str(raised.value)
    assert "ghs_secret" not in str(raised.value)


def test_missing_installation_is_reported_clearly(key_file: Path) -> None:
    api = Api()
    api.on("GET", "/repos/acme/shop/installation", _json({"message": "Not Found"}, status=404))

    with pytest.raises(IssueTrackerError, match="nicht installiert"):
        _tracker(api, key_file).get(REPO, 7)
