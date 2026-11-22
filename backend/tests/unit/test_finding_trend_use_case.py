from datetime import UTC, datetime

import pytest

from app.application.finding_trend import GetFindingTrend
from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import Finding, RiskScore, Severity
from tests.fakes import InMemoryUnitOfWork

_NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
_SEEN = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)


def _add_application_with_finding(uow: InMemoryUnitOfWork, name: str) -> int:
    application = uow.applications.add(Application(name=name))
    assert application.id is not None
    component = uow.components.add(
        application.id, Component("react", "1.0", Category.LIBRARY, Ecosystem.NPM, True)
    )
    assert component.id is not None
    uow.findings.upsert(
        Finding(
            "CVE-1",
            component.id,
            application.id,
            "1.0",
            RiskScore(value=75, level=Severity.HOCH, rationale=""),
            first_seen_at=_SEEN,
        )
    )
    return application.id


def _use_case(uow: InMemoryUnitOfWork) -> GetFindingTrend:
    return GetFindingTrend(uow, lambda: _NOW)


def test_trend_for_all_applications() -> None:
    uow = InMemoryUnitOfWork()
    _add_application_with_finding(uow, "Shop")
    _add_application_with_finding(uow, "Blog")
    assert _use_case(uow).execute(weeks=4).untouched_now == 2


def test_trend_scoped_to_application() -> None:
    uow = InMemoryUnitOfWork()
    shop_id = _add_application_with_finding(uow, "Shop")
    _add_application_with_finding(uow, "Blog")
    trend = _use_case(uow).execute(weeks=4, application_id=shop_id)
    assert trend.untouched_now == 1
    assert trend.new_total == 1


def test_trend_unknown_application_raises() -> None:
    with pytest.raises(EntityNotFoundError):
        _use_case(InMemoryUnitOfWork()).execute(weeks=4, application_id=999)
