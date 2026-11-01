"""Ingest: fragt OSV je Komponente ab und legt Advisories + Funde an.

In Stufe 1 laeuft dieser Use Case synchron; spaeter stoesst ihn ein Worker an.
"""

from dataclasses import dataclass, replace

from app.application.risk_score import compute_risk_score
from app.application.unit_of_work import UnitOfWork
from app.domain.inventory import Component
from app.domain.ports import AdvisoryStore, OsvClient, SourceReference, SourceVuln
from app.domain.vulnerability import Advisory, Finding


@dataclass(frozen=True)
class IngestResult:
    components_scanned: int
    findings_found: int


@dataclass(frozen=True)
class _Target:
    """Aufgeloeste Koordinaten einer zu scannenden Komponente."""

    ecosystem: str
    package: str
    component_id: int
    application_id: int
    version: str


def _advisory_id_and_cve(vuln: SourceVuln) -> tuple[str, str | None]:
    for alias in vuln.aliases:
        if alias.startswith("CVE-"):
            return alias, alias
    return vuln.id, None


def _source_url(vuln: SourceVuln) -> str:
    if vuln.references:
        return vuln.references[0]
    return f"https://osv.dev/vulnerability/{vuln.id}"


def _render_body(vuln: SourceVuln, rationale: str) -> str:
    lines = [vuln.details or vuln.summary, "", "# Computation", rationale]
    if vuln.references:
        lines += ["", "# References", *[f"- {url}" for url in vuln.references]]
    return "\n".join(lines)


class RunIngest:
    def __init__(self, uow: UnitOfWork, osv: OsvClient, store: AdvisoryStore) -> None:
        self._uow = uow
        self._osv = osv
        self._store = store

    def execute(self) -> IngestResult:
        components = [
            c
            for c in self._uow.components.list_all()
            if c.ecosystem is not None and c.id is not None and c.application_id is not None
        ]
        found = sum(self._scan(component) for component in components)
        self._uow.commit()
        return IngestResult(components_scanned=len(components), findings_found=found)

    def _scan(self, component: Component) -> int:
        ecosystem = component.ecosystem
        component_id = component.id
        application_id = component.application_id
        assert ecosystem is not None
        assert component_id is not None
        assert application_id is not None
        target = _Target(
            ecosystem=ecosystem.value,
            package=component.name,
            component_id=component_id,
            application_id=application_id,
            version=component.version,
        )
        vulns = self._osv.query(ecosystem.value, component.name, component.version)
        for vuln in vulns:
            self._store_vuln(vuln, target)
        return len(vulns)

    def _store_vuln(self, vuln: SourceVuln, target: _Target) -> None:
        advisory_id, cve_id = _advisory_id_and_cve(vuln)
        risk = compute_risk_score(vuln.cvss_base)
        advisory = Advisory(
            advisory_id=advisory_id,
            cve_id=cve_id,
            title=vuln.summary or advisory_id,
            description=vuln.summary,
            cvss_base=vuln.cvss_base,
            fixed_version=vuln.fixed_version,
            references=vuln.references,
            okf_path="",
        )
        okf_path = self._store.save(
            advisory,
            tags=[target.ecosystem, target.package],
            sources=[SourceReference("osv", _source_url(vuln))],
            body=_render_body(vuln, risk.rationale),
        )
        self._uow.advisories.upsert(replace(advisory, okf_path=okf_path))
        self._uow.findings.upsert(
            Finding(
                advisory_id=advisory_id,
                component_id=target.component_id,
                application_id=target.application_id,
                found_version=target.version,
                risk=risk,
            )
        )
