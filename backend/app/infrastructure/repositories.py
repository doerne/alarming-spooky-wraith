"""SQLAlchemy-Repositories: Abbildung zwischen Domaene und Modellen."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import Advisory, Finding, FindingStatus, RiskScore, Severity
from app.infrastructure.models import (
    AdvisoryModel,
    ApplicationModel,
    ComponentModel,
    FindingModel,
)


def _to_application(model: ApplicationModel) -> Application:
    return Application(name=model.name, description=model.description, id=model.id)


def _to_component(model: ComponentModel) -> Component:
    return Component(
        name=model.name,
        version=model.version,
        category=Category(model.category),
        ecosystem=Ecosystem(model.ecosystem) if model.ecosystem else None,
        direct=model.direct,
        id=model.id,
        application_id=model.application_id,
    )


def _to_advisory(model: AdvisoryModel) -> Advisory:
    return Advisory(
        advisory_id=model.advisory_id,
        cve_id=model.cve_id,
        title=model.title,
        description=model.description,
        cvss_base=model.cvss_score,
        fixed_version=model.fix_version,
        references=[],
        okf_path=model.okf_path,
    )


def _to_finding(model: FindingModel) -> Finding:
    return Finding(
        advisory_id=model.advisory_id,
        component_id=model.component_id,
        application_id=model.application_id,
        found_version=model.found_version,
        risk=RiskScore(value=model.risk_score, level=Severity(model.risk_level), rationale=""),
        status=FindingStatus(model.status),
        comment=model.comment,
        id=model.id,
    )


class SqlAlchemyApplicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, application: Application) -> Application:
        model = ApplicationModel(name=application.name, description=application.description)
        self._session.add(model)
        self._session.flush()
        application.id = model.id
        return application

    def get(self, application_id: int) -> Application:
        model = self._session.get(ApplicationModel, application_id)
        if model is None:
            raise EntityNotFoundError("Anwendung", application_id)
        return _to_application(model)

    def list(self) -> list[Application]:
        models = self._session.scalars(select(ApplicationModel)).all()
        return [_to_application(model) for model in models]


class SqlAlchemyComponentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, application_id: int, component: Component) -> Component:
        model = ComponentModel(
            application_id=application_id,
            name=component.name,
            version=component.version,
            category=component.category.value,
            ecosystem=component.ecosystem.value if component.ecosystem else None,
            direct=component.direct,
        )
        self._session.add(model)
        self._session.flush()
        return _to_component(model)

    def get(self, component_id: int) -> Component:
        model = self._session.get(ComponentModel, component_id)
        if model is None:
            raise EntityNotFoundError("Komponente", component_id)
        return _to_component(model)

    def update(self, component: Component) -> Component:
        assert component.id is not None
        model = self._session.get(ComponentModel, component.id)
        if model is None:
            raise EntityNotFoundError("Komponente", component.id)
        model.name = component.name
        model.version = component.version
        model.category = component.category.value
        model.ecosystem = component.ecosystem.value if component.ecosystem else None
        model.direct = component.direct
        self._session.flush()
        return _to_component(model)

    def list_all(self) -> list[Component]:
        models = self._session.scalars(select(ComponentModel)).all()
        return [_to_component(model) for model in models]

    def list_for_application(self, application_id: int) -> list[Component]:
        models = self._session.scalars(
            select(ComponentModel).where(ComponentModel.application_id == application_id)
        ).all()
        return [_to_component(model) for model in models]


class SqlAlchemyAdvisoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, advisory: Advisory) -> Advisory:
        model = self._session.get(AdvisoryModel, advisory.advisory_id)
        if model is None:
            model = AdvisoryModel(advisory_id=advisory.advisory_id)
            self._session.add(model)
        model.cve_id = advisory.cve_id
        model.okf_path = advisory.okf_path
        model.title = advisory.title
        model.description = advisory.description
        model.cvss_score = advisory.cvss_base
        model.fix_version = advisory.fixed_version
        self._session.flush()
        return advisory

    def get(self, advisory_id: str) -> Advisory:
        model = self._session.get(AdvisoryModel, advisory_id)
        if model is None:
            raise EntityNotFoundError("Advisory", advisory_id)
        return _to_advisory(model)


class SqlAlchemyFindingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, finding: Finding) -> Finding:
        model = self._session.scalars(
            select(FindingModel).where(
                FindingModel.advisory_id == finding.advisory_id,
                FindingModel.component_id == finding.component_id,
            )
        ).one_or_none()
        if model is None:
            model = FindingModel(
                advisory_id=finding.advisory_id,
                component_id=finding.component_id,
                application_id=finding.application_id,
            )
            self._session.add(model)
        model.found_version = finding.found_version
        model.risk_score = finding.risk.value
        model.risk_level = finding.risk.level.value
        model.status = finding.status.value
        model.comment = finding.comment
        self._session.flush()
        finding.id = model.id
        return finding

    def list(self) -> list[Finding]:
        models = self._session.scalars(select(FindingModel)).all()
        return [_to_finding(model) for model in models]
