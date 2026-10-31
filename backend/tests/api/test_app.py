from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.errors import DomainError, EntityNotFoundError
from app.presentation.app_factory import create_app
from tests.fakes import InMemoryUnitOfWork


@pytest.fixture
def app(uow: InMemoryUnitOfWork) -> FastAPI:
    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    return create_app(factory)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_docs_are_disabled_by_default(client: TestClient) -> None:
    assert client.get("/api/docs").status_code == 404


def test_domain_errors_are_mapped_to_http_status(app: FastAPI) -> None:
    @app.get("/api/_test/not-found")
    def not_found() -> None:
        raise EntityNotFoundError("Bestellung", 1)

    @app.get("/api/_test/domain-error")
    def domain_error() -> None:
        raise DomainError("Regel verletzt")

    with TestClient(app) as client:
        assert client.get("/api/_test/not-found").status_code == 404
        response = client.get("/api/_test/domain-error")
        assert response.status_code == 400
        assert response.json() == {"detail": "Regel verletzt"}
