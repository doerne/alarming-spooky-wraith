"""SQLAlchemy-Repositories: Abbildung zwischen Domaene und Modellen."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.sbom import Sbom, SbomEntry, SbomVersion
from app.domain.sources import RunStatus, SourceSetting
from app.domain.vulnerability import Advisory, Finding, FindingStatus, RiskScore, Severity
from app.infrastructure.models import (
    AdvisoryModel,
    ApplicationModel,
    ComponentModel,
    FindingModel,
    SbomModel,
    SbomVersionModel,
    SourceSettingModel,
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
        sbom_id=model.sbom_id,
        checked=model.checked,
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
            sbom_id=component.sbom_id,
            checked=component.checked,
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
        model.sbom_id = component.sbom_id
        model.checked = component.checked
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

    def list_for_sbom(self, sbom_id: int) -> list[Component]:
        models = self._session.scalars(
            select(ComponentModel).where(ComponentModel.sbom_id == sbom_id)
        ).all()
        return [_to_component(model) for model in models]

    def delete(self, component_id: int) -> None:
        self._session.execute(delete(ComponentModel).where(ComponentModel.id == component_id))


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
            # Triage-Felder nur beim Anlegen setzen; ein erneuter Fund behält sie.
            model = FindingModel(
                advisory_id=finding.advisory_id,
                component_id=finding.component_id,
                application_id=finding.application_id,
                status=finding.status.value,
                comment=finding.comment,
            )
            self._session.add(model)
        model.found_version = finding.found_version
        model.risk_score = finding.risk.value
        model.risk_level = finding.risk.level.value
        self._session.flush()
        finding.id = model.id
        finding.status = FindingStatus(model.status)
        finding.comment = model.comment
        return finding

    def list(self) -> list[Finding]:
        models = self._session.scalars(select(FindingModel)).all()
        return [_to_finding(model) for model in models]

    def delete_for_component(self, component_id: int) -> None:
        self._session.execute(delete(FindingModel).where(FindingModel.component_id == component_id))


def _entry_to_json(entry: SbomEntry) -> dict[str, object]:
    return {
        "name": entry.name,
        "version": entry.version,
        "category": entry.category.value,
        "ecosystem": entry.ecosystem.value if entry.ecosystem else None,
        "direct": entry.direct,
        "purl": entry.purl,
    }


def _entry_from_json(raw: dict[str, object]) -> SbomEntry:
    ecosystem = raw.get("ecosystem")
    purl = raw.get("purl")
    return SbomEntry(
        name=str(raw["name"]),
        version=str(raw["version"]),
        category=Category(str(raw["category"])),
        ecosystem=Ecosystem(str(ecosystem)) if ecosystem else None,
        direct=bool(raw["direct"]),
        purl=str(purl) if purl else None,
    )


def _to_sbom(model: SbomModel) -> Sbom:
    return Sbom(application_id=model.application_id, name=model.name, id=model.id)


def _to_sbom_version(model: SbomVersionModel) -> SbomVersion:
    return SbomVersion(
        sbom_id=model.sbom_id,
        label=model.label,
        uploaded_at=model.uploaded_at,
        serial_number=model.serial_number,
        is_current=model.is_current,
        entries=tuple(_entry_from_json(raw) for raw in model.components),
        id=model.id,
    )


class SqlAlchemySbomRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, sbom: Sbom) -> Sbom:
        model = SbomModel(application_id=sbom.application_id, name=sbom.name)
        self._session.add(model)
        self._session.flush()
        sbom.id = model.id
        return sbom

    def get(self, sbom_id: int) -> Sbom:
        model = self._session.get(SbomModel, sbom_id)
        if model is None:
            raise EntityNotFoundError("SBOM", sbom_id)
        return _to_sbom(model)

    def find_by_name(self, application_id: int, name: str) -> Sbom | None:
        model = self._session.scalars(
            select(SbomModel).where(
                SbomModel.application_id == application_id, SbomModel.name == name
            )
        ).one_or_none()
        return _to_sbom(model) if model else None

    def list_for_application(self, application_id: int) -> list[Sbom]:
        models = self._session.scalars(
            select(SbomModel).where(SbomModel.application_id == application_id)
        ).all()
        return [_to_sbom(model) for model in models]

    def delete(self, sbom_id: int) -> None:
        self._session.execute(delete(SbomVersionModel).where(SbomVersionModel.sbom_id == sbom_id))
        self._session.execute(delete(SbomModel).where(SbomModel.id == sbom_id))


class SqlAlchemySbomVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, version: SbomVersion) -> SbomVersion:
        model = SbomVersionModel(
            sbom_id=version.sbom_id,
            label=version.label,
            uploaded_at=version.uploaded_at,
            serial_number=version.serial_number,
            is_current=version.is_current,
            components=[_entry_to_json(entry) for entry in version.entries],
        )
        self._session.add(model)
        self._session.flush()
        return _to_sbom_version(model)

    def get(self, version_id: int) -> SbomVersion:
        model = self._session.get(SbomVersionModel, version_id)
        if model is None:
            raise EntityNotFoundError("SBOM-Version", version_id)
        return _to_sbom_version(model)

    def current_for_sbom(self, sbom_id: int) -> SbomVersion | None:
        model = self._session.scalars(
            select(SbomVersionModel)
            .where(SbomVersionModel.sbom_id == sbom_id, SbomVersionModel.is_current.is_(True))
            .order_by(SbomVersionModel.id.desc())
        ).first()
        return _to_sbom_version(model) if model else None

    def list_for_sbom(self, sbom_id: int) -> list[SbomVersion]:
        models = self._session.scalars(
            select(SbomVersionModel)
            .where(SbomVersionModel.sbom_id == sbom_id)
            .order_by(SbomVersionModel.id.desc())
        ).all()
        return [_to_sbom_version(model) for model in models]

    def archive(self, version_id: int) -> None:
        model = self._session.get(SbomVersionModel, version_id)
        if model is None:
            raise EntityNotFoundError("SBOM-Version", version_id)
        model.is_current = False
        self._session.flush()


def _to_source_setting(model: SourceSettingModel) -> SourceSetting:
    return SourceSetting(
        source_key=model.source_key,
        enabled=model.enabled,
        api_key=model.api_key,
        last_run_at=model.last_run_at,
        last_status=RunStatus(model.last_status) if model.last_status else None,
        last_message=model.last_message,
        last_findings=model.last_findings,
    )


class SqlAlchemySourceSettingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_all(self) -> list[SourceSetting]:
        models = self._session.scalars(select(SourceSettingModel)).all()
        return [_to_source_setting(model) for model in models]

    def get(self, source_key: str) -> SourceSetting | None:
        model = self._session.get(SourceSettingModel, source_key)
        return _to_source_setting(model) if model else None

    def save(self, setting: SourceSetting) -> None:
        model = self._session.get(SourceSettingModel, setting.source_key)
        if model is None:
            model = SourceSettingModel(source_key=setting.source_key)
            self._session.add(model)
        model.enabled = setting.enabled
        model.api_key = setting.api_key
        model.last_run_at = setting.last_run_at
        model.last_status = setting.last_status.value if setting.last_status else None
        model.last_message = setting.last_message
        model.last_findings = setting.last_findings
        self._session.flush()
