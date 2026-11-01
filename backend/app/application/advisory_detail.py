"""Use Case: alle gespeicherten Infos zu einer Advisory für die Detailansicht."""

from dataclasses import dataclass

from app.application.risk_score import compute_risk_score
from app.application.unit_of_work import UnitOfWork
from app.domain.inventory import Component
from app.domain.ports import AdvisoryDocument, AdvisoryStore, SourceReference
from app.domain.vulnerability import Advisory, Finding, FindingStatus, Severity


@dataclass(frozen=True)
class AffectedFinding:
    application_name: str
    component_id: int
    component_name: str
    component_version: str
    ecosystem: str | None
    risk_score: int
    risk_level: Severity
    status: FindingStatus


@dataclass(frozen=True)
class AdvisoryDetail:
    advisory_id: str
    cve_id: str | None
    title: str
    cvss_base: float | None
    fix_version: str | None
    risk_score: int
    risk_level: Severity
    description: str
    rationale: str
    references: list[str]
    sources: list[SourceReference]
    findings: list[AffectedFinding]


class GetAdvisoryDetail:
    def __init__(self, uow: UnitOfWork, store: AdvisoryStore) -> None:
        self._uow = uow
        self._store = store

    def execute(self, advisory_id: str) -> AdvisoryDetail:
        advisory = self._uow.advisories.get(advisory_id)
        findings = self._findings(advisory_id)
        # Ohne Datei bleibt die Anzeige nutzbar: Beschreibung aus der DB.
        document = self._store.read_document(advisory_id) or AdvisoryDocument(
            advisory.description, "", [], []
        )
        return _detail(advisory, document, findings)

    def _findings(self, advisory_id: str) -> list[AffectedFinding]:
        components = {c.id: c for c in self._uow.components.list_all() if c.id is not None}
        views = [
            self._to_view(finding, components[finding.component_id])
            for finding in self._uow.findings.list()
            if finding.advisory_id == advisory_id and finding.component_id in components
        ]
        return sorted(views, key=lambda view: view.risk_score, reverse=True)

    def _to_view(self, finding: Finding, component: Component) -> AffectedFinding:
        assert component.id is not None
        return AffectedFinding(
            application_name=self._uow.applications.get(finding.application_id).name,
            component_id=component.id,
            component_name=component.name,
            component_version=component.version,
            ecosystem=component.ecosystem.value if component.ecosystem else None,
            risk_score=finding.risk.value,
            risk_level=finding.risk.level,
            status=finding.status,
        )


def _detail(
    advisory: Advisory, document: AdvisoryDocument, findings: list[AffectedFinding]
) -> AdvisoryDetail:
    # Kopf-Risiko: höchster Fund; ohne Funde aus dem CVSS-Wert berechnet.
    risk = compute_risk_score(advisory.cvss_base)
    score, level = (
        (findings[0].risk_score, findings[0].risk_level) if findings else (risk.value, risk.level)
    )
    return AdvisoryDetail(
        advisory_id=advisory.advisory_id,
        cve_id=advisory.cve_id,
        title=advisory.title,
        cvss_base=advisory.cvss_base,
        fix_version=advisory.fixed_version,
        risk_score=score,
        risk_level=level,
        description=document.description,
        rationale=document.rationale,
        references=document.references,
        sources=document.sources,
        findings=findings,
    )
