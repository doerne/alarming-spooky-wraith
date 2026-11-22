from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from httpx import Response

from app.infrastructure.sbom.cyclonedx import CycloneDxParser
from app.presentation.app_factory import AppServices, create_app
from tests.fakes import InMemoryUnitOfWork

_NOW = datetime(2026, 11, 21, 9, 30, tzinfo=UTC)


def _client() -> TestClient:
    uow = InMemoryUnitOfWork()

    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    app = create_app(
        factory, services=AppServices(sbom_parser=CycloneDxParser(), clock=lambda: _NOW)
    )
    return TestClient(app)


def _library(name: str, version: str, purl: str | None) -> dict[str, object]:
    component: dict[str, object] = {"type": "library", "name": name, "version": version}
    if purl:
        component["purl"] = purl
    return component


def _document(*components: dict[str, object], serial: str = "urn:uuid:1") -> dict[str, object]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": serial,
        "metadata": {"component": {"name": "backend", "version": "1.4.0"}},
        "components": list(components),
    }


_REACT = _library("react", "18.2.0", "pkg:npm/react@18.2.0")
_OPENSSL = _library("openssl", "3.0.11", "pkg:deb/debian/openssl@3.0.11")


def _application(client: TestClient) -> int:
    application_id: int = client.post("/api/applications", json={"name": "Shop"}).json()["id"]
    return application_id


def _upload(client: TestClient, application_id: int, document: dict[str, object]) -> Response:
    response: Response = client.post(
        f"/api/applications/{application_id}/sboms/versions",
        json={"name": "backend-image", "label": None, "document": document},
    )
    return response


def test_upload_sbom_returns_summary() -> None:
    client = _client()
    application_id = _application(client)
    response = _upload(client, application_id, _document(_REACT, _OPENSSL))
    assert response.status_code == 201
    body = response.json()
    assert (body["added"], body["removed"], body["kept"], body["unchecked"]) == (2, 0, 0, 1)
    assert body["version"]["isCurrent"] is True
    assert body["version"]["label"] == "1.4.0"
    assert body["version"]["componentCount"] == 2
    assert body["version"]["uncheckedCount"] == 1


def test_upload_same_serial_twice_returns_409() -> None:
    client = _client()
    application_id = _application(client)
    _upload(client, application_id, _document(_REACT))
    response = _upload(client, application_id, _document(_REACT))
    assert response.status_code == 409
    assert "bereits" in response.json()["detail"]


def test_upload_invalid_document_returns_422() -> None:
    client = _client()
    application_id = _application(client)
    response = _upload(client, application_id, {"spdxVersion": "SPDX-2.3"})
    assert response.status_code == 422
    assert "CycloneDX" in response.json()["detail"]


def test_upload_for_unknown_application_returns_404() -> None:
    response = _upload(_client(), 999, _document(_REACT))
    assert response.status_code == 404


def test_list_sboms_and_versions_and_get_archived_version() -> None:
    client = _client()
    application_id = _application(client)
    first = _upload(client, application_id, _document(_REACT, _OPENSSL)).json()
    _upload(client, application_id, _document(_REACT, serial="urn:uuid:2"))
    sbom_id = first["sbomId"]

    sboms = client.get(f"/api/applications/{application_id}/sboms").json()
    assert [(s["name"], s["versionCount"]) for s in sboms] == [("backend-image", 2)]
    assert sboms[0]["current"]["componentCount"] == 1

    versions = client.get(f"/api/applications/{application_id}/sboms/{sbom_id}/versions").json()
    assert [v["isCurrent"] for v in versions] == [True, False]
    assert "components" not in versions[0]

    archived_id = first["version"]["id"]
    archived = client.get(
        f"/api/applications/{application_id}/sboms/{sbom_id}/versions/{archived_id}"
    ).json()
    assert archived["isCurrent"] is False
    assert [(c["name"], c["checked"]) for c in archived["components"]] == [
        ("react", True),
        ("openssl", False),
    ]
    assert archived["components"][1]["purl"] == "pkg:deb/debian/openssl@3.0.11"


def test_sbom_of_other_application_returns_404() -> None:
    client = _client()
    owner = _application(client)
    other = _application(client)
    sbom_id = _upload(client, owner, _document(_REACT)).json()["sbomId"]
    assert client.get(f"/api/applications/{other}/sboms/{sbom_id}/versions").status_code == 404
    assert client.delete(f"/api/applications/{other}/sboms/{sbom_id}").status_code == 404


def test_delete_sbom_returns_204_and_removes_components() -> None:
    client = _client()
    application_id = _application(client)
    sbom_id = _upload(client, application_id, _document(_REACT)).json()["sbomId"]
    response = client.delete(f"/api/applications/{application_id}/sboms/{sbom_id}")
    assert response.status_code == 204
    detail = client.get(f"/api/applications/{application_id}").json()
    assert detail["components"] == []
    assert client.get(f"/api/applications/{application_id}/sboms").json() == []


def test_component_response_has_sbom_id_and_checked() -> None:
    client = _client()
    application_id = _application(client)
    sbom_id = _upload(client, application_id, _document(_OPENSSL)).json()["sbomId"]
    component = client.get(f"/api/applications/{application_id}").json()["components"][0]
    assert component["sbomId"] == sbom_id
    assert component["checked"] is False


def test_update_sbom_component_returns_409() -> None:
    client = _client()
    application_id = _application(client)
    _upload(client, application_id, _document(_REACT))
    component = client.get(f"/api/applications/{application_id}").json()["components"][0]
    response = client.put(
        f"/api/applications/{application_id}/components/{component['id']}",
        json={"name": "react", "version": "18.3.1", "category": "library", "ecosystem": "npm"},
    )
    assert response.status_code == 409


def test_upload_rejects_too_long_name() -> None:
    client = _client()
    application_id = _application(client)
    response = client.post(
        f"/api/applications/{application_id}/sboms/versions",
        json={"name": "x" * 101, "document": _document(_REACT)},
    )
    assert response.status_code == 422
