from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.application.source_registry import SourceRegistry
from app.domain.sources import ApiKeyRequirement
from app.presentation.app_factory import AppServices, create_app
from tests.fakes import FakeBulkSource, FakePackageSource, InMemoryUnitOfWork, descriptor

_SECRET = "org-123:tok-very-secret"


def _client() -> TestClient:
    uow = InMemoryUnitOfWork()

    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    registry = SourceRegistry(
        [
            FakePackageSource(descriptor("osv")),
            FakePackageSource(descriptor("snyk", requirement=ApiKeyRequirement.REQUIRED)),
            FakeBulkSource(descriptor("rustsec")),
        ]
    )
    return TestClient(create_app(factory, services=AppServices(source_registry=registry)))


def test_list_sources_returns_registry_entries() -> None:
    body = _client().get("/api/sources").json()
    assert [item["key"] for item in body] == ["osv", "snyk", "rustsec"]
    snyk = body[1]
    assert snyk["status"] == "missing_key"
    assert snyk["apiKeyRequirement"] == "required"
    assert snyk["apiKeyHint"] == "Format <a>:<b>"
    assert snyk["hasApiKey"] is False
    assert snyk["enabled"] is True
    assert snyk["homepageUrl"] == "https://snyk.example.org"
    assert snyk["lastStatus"] is None


def test_toggle_source() -> None:
    client = _client()
    response = client.patch("/api/sources/osv", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["status"] == "disabled"
    assert client.get("/api/sources").json()[0]["enabled"] is False


def test_api_key_is_never_returned() -> None:
    client = _client()
    response = client.put("/api/sources/snyk/api-key", json={"apiKey": _SECRET})
    assert response.status_code == 200
    assert response.json()["hasApiKey"] is True
    assert response.json()["status"] == "ready"
    assert _SECRET not in response.text
    assert _SECRET not in client.get("/api/sources").text


def test_blank_api_key_is_rejected() -> None:
    client = _client()
    response = client.put("/api/sources/snyk/api-key", json={"apiKey": "   "})
    assert response.status_code == 422
    assert client.get("/api/sources").json()[1]["hasApiKey"] is False


def test_remove_api_key() -> None:
    client = _client()
    client.put("/api/sources/snyk/api-key", json={"apiKey": _SECRET})
    response = client.delete("/api/sources/snyk/api-key")
    assert response.status_code == 200
    assert response.json()["hasApiKey"] is False


def test_unknown_source_is_404() -> None:
    assert _client().patch("/api/sources/nope", json={"enabled": True}).status_code == 404
