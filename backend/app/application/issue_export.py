"""Use Case: offene CVEs einer Anwendung als Vorlagen für GitHub-Issues sammeln."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from app.application.risk_score import compute_risk_score
from app.application.unit_of_work import UnitOfWork
from app.domain.inventory import Component
from app.domain.ports import AdvisoryDocument, AdvisoryStore
from app.domain.vulnerability import Advisory, Finding, FindingStatus, Severity

EXPORTED_STATUSES = frozenset({FindingStatus.OPEN, FindingStatus.IN_PROGRESS})
DESCRIPTION_MAX_LENGTH = 4_000
REFERENCES_MAX = 10
MANUAL_SOURCE = "manuell"
_TRUNCATION_MARK = "…"


@dataclass(frozen=True)
class AffectedComponent:
    name: str
    found_version: str
    ecosystem: str | None
    source: str
    status: FindingStatus
    comment: str


@dataclass(frozen=True)
class IssueDraft:
    advisory_id: str
    cve_id: str | None
    title: str
    risk_score: int
    risk_level: Severity
    rationale: str
    cvss_base: float | None
    fix_version: str | None
    description: str
    references: tuple[str, ...]
    components: tuple[AffectedComponent, ...]
    issue_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class IssueExport:
    application_id: int
    application_name: str
    generated_at: datetime
    issues: tuple[IssueDraft, ...]


def _truncate(text: str) -> str:
    if len(text) <= DESCRIPTION_MAX_LENGTH:
        return text
    return text[:DESCRIPTION_MAX_LENGTH] + _TRUNCATION_MARK


def _draft(
    advisory: Advisory,
    document: AdvisoryDocument | None,
    components: Sequence[AffectedComponent],
    findings: Sequence[Finding],
) -> IssueDraft:
    top = findings[0]
    rationale = document.rationale if document and document.rationale else ""
    references = document.references if document and document.references else advisory.references
    description = document.description if document and document.description else ""
    description = description or advisory.description
    return IssueDraft(
        advisory_id=advisory.advisory_id,
        cve_id=advisory.cve_id,
        title=advisory.title,
        risk_score=top.risk.value,
        risk_level=top.risk.level,
        rationale=rationale or compute_risk_score(advisory.cvss_base).rationale,
        cvss_base=advisory.cvss_base,
        fix_version=advisory.fixed_version,
        description=_truncate(description),
        references=tuple(references[:REFERENCES_MAX]),
        components=tuple(components),
        issue_urls=tuple(
            dict.fromkeys(finding.issue_url for finding in findings if finding.issue_url)
        ),
    )


class ExportApplicationIssues:
    def __init__(
        self, uow: UnitOfWork, store: AdvisoryStore, clock: Callable[[], datetime]
    ) -> None:
        self._uow = uow
        self._store = store
        self._clock = clock

    def execute(self, application_id: int) -> IssueExport:
        application = self._uow.applications.get(application_id)  # EntityNotFoundError
        components = {
            component.id: component
            for component in self._uow.components.list_for_application(application_id)
            if component.checked
        }
        groups: dict[str, list[Finding]] = {}
        for finding in self._uow.findings.list():
            if self._is_exported(finding, application_id, components):
                groups.setdefault(finding.advisory_id, []).append(finding)
        drafts = [self._to_draft(findings, components) for findings in groups.values()]
        drafts.sort(key=lambda draft: (-draft.risk_score, draft.advisory_id))
        return IssueExport(
            application_id=application_id,
            application_name=application.name,
            generated_at=self._clock(),
            issues=tuple(drafts),
        )

    @staticmethod
    def _is_exported(
        finding: Finding, application_id: int, components: dict[int | None, Component]
    ) -> bool:
        return (
            finding.application_id == application_id
            and finding.status in EXPORTED_STATUSES
            and finding.component_id in components
        )

    def _to_draft(
        self, findings: list[Finding], components: dict[int | None, Component]
    ) -> IssueDraft:
        ordered = sorted(findings, key=lambda finding: finding.risk.value, reverse=True)
        affected = [
            self._affected(finding, components[finding.component_id]) for finding in ordered
        ]
        advisory = self._uow.advisories.get(ordered[0].advisory_id)
        document = self._store.read_document(advisory.advisory_id)
        return _draft(advisory, document, affected, ordered)

    def _affected(self, finding: Finding, component: Component) -> AffectedComponent:
        return AffectedComponent(
            name=component.name,
            found_version=finding.found_version,
            ecosystem=component.ecosystem.value if component.ecosystem else None,
            source=self._source(component),
            status=finding.status,
            comment=finding.comment,
        )

    def _source(self, component: Component) -> str:
        if component.sbom_id is None:
            return MANUAL_SOURCE
        return self._uow.sboms.get(component.sbom_id).name
