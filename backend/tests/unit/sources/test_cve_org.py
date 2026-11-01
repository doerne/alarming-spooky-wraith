import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest

from app.domain.errors import SourceAccessError
from app.domain.ports import AffectedPackage, RangeEvent
from app.infrastructure.sources.cve_org import CveOrgSource
from app.infrastructure.sources.http_cache import HttpCache
from tests.unit.sources.helpers import mock_client

_RELEASE = {
    "assets": [
        {"name": "2026-11-01_delta_CVEs_at_1300Z.zip", "browser_download_url": "https://dl/delta"},
        {
            "name": "2026-11-01_all_CVEs_at_midnight.zip.zip",
            "browser_download_url": "https://dl/all",
        },
    ]
}


def _record(cve_id: str, product: str, state: str = "PUBLISHED") -> dict[str, object]:
    return {
        "cveMetadata": {"cveId": cve_id, "state": state},
        "containers": {
            "cna": {
                "descriptions": [{"lang": "en", "value": f"bug in {product}"}],
                "affected": [
                    {
                        "vendor": "x",
                        "product": product,
                        "versions": [
                            {"version": "7.0", "lessThan": "7.2.5", "status": "affected"},
                            {"version": "6.2.1", "status": "affected"},
                            {"version": "8.0", "status": "unaffected"},
                        ],
                    }
                ],
                "metrics": [{"cvssV3_1": {"baseScore": 7.5}}],
                "references": [{"url": "https://ref"}],
            }
        },
    }


def _nested_zip(records: list[dict[str, object]]) -> bytes:
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as archive:
        for record in records:
            cve_id = record["cveMetadata"]["cveId"]  # type: ignore[index]
            archive.writestr(f"cves/2024/0xxx/{cve_id}.json", json.dumps(record))
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as archive:
        archive.writestr("cves.zip", inner.getvalue())
    return outer.getvalue()


def _source(tmp_path: Path, records: list[dict[str, object]]) -> CveOrgSource:
    payload = _nested_zip(records)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.github.com":
            return httpx.Response(200, json=_RELEASE)
        assert str(request.url) == "https://dl/all"
        return httpx.Response(200, content=payload)

    client = mock_client(handler)
    return CveOrgSource(client, HttpCache(tmp_path, client))


def test_cve_org_maps_record(tmp_path: Path) -> None:
    records = [
        _record("CVE-2024-1", "Redis"),
        _record("CVE-2024-2", "nginx"),
        _record("CVE-2024-3", "redis", state="REJECTED"),
    ]
    vulns = _source(tmp_path, records).load(None, frozenset({"redis"}))
    assert [vuln.id for vuln in vulns] == ["CVE-2024-1"]
    vuln = vulns[0]
    assert vuln.cvss_base == 7.5
    assert vuln.url == "https://www.cve.org/CVERecord?id=CVE-2024-1"
    assert vuln.affected == (
        AffectedPackage(
            None,
            "redis",
            (RangeEvent("introduced", "7.0"), RangeEvent("fixed", "7.2.5")),
            ("6.2.1",),
        ),
    )


def test_cve_org_without_names_loads_nothing(tmp_path: Path) -> None:
    assert _source(tmp_path, [_record("CVE-2024-1", "redis")]).load(None, frozenset()) == []


def test_cve_org_http_error_raises_source_access_error(tmp_path: Path) -> None:
    client = mock_client(lambda _: httpx.Response(503))
    with pytest.raises(SourceAccessError, match="nicht erreichbar"):
        CveOrgSource(client, HttpCache(tmp_path, client)).load(None, frozenset({"redis"}))
