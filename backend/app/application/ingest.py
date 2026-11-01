"""Ingest: fragt alle aktiven Quellen ab und legt Advisories und Funde an.

Ablauf: pro Quelle sammeln (Fehler einer Quelle brechen den Lauf nicht ab),
dann je Advisory über alle Quellen zusammenführen und einmal schreiben.
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import cast

from app.application.advisory_merge import MergedAdvisory, advisory_key, merge_vulns
from app.application.component_matching import ComponentMatcher, normalize_package_name
from app.application.risk_score import compute_risk_score
from app.application.source_registry import SourceRegistry
from app.application.source_use_cases import load_setting
from app.application.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.domain.errors import SourceAccessError
from app.domain.inventory import Component
from app.domain.ports import (
    AdvisoryStore,
    BulkSource,
    PackageQuerySource,
    SourceVuln,
    VulnerabilitySource,
)
from app.domain.sources import (
    MERGE_PRECEDENCE,
    MatchScope,
    RunStatus,
    SourceDescriptor,
    SourceKind,
    SourceSetting,
    SourceStatus,
    source_status,
)
from app.domain.vulnerability import Advisory, Finding

_logger = logging.getLogger(__name__)
_MAX_MESSAGE_LENGTH = 500
_SKIP_MESSAGES = {
    SourceStatus.DISABLED: "deaktiviert",
    SourceStatus.MISSING_KEY: "API-Key fehlt",
}

Clock = Callable[[], datetime]


@dataclass(frozen=True)
class SourceRunResult:
    source_key: str
    status: RunStatus
    findings: int
    message: str


@dataclass(frozen=True)
class IngestResult:
    components_scanned: int
    findings_found: int
    sources: list[SourceRunResult]


@dataclass(frozen=True)
class _Hit:
    """Eine Schwachstelle, die eine Quelle für eine Komponente geliefert hat."""

    component: Component
    vuln: SourceVuln


def in_scope(descriptor: SourceDescriptor, component: Component) -> bool:
    """Ob eine Quelle diese Komponente abgleicht (Spec §7)."""
    ecosystem = component.ecosystem.value if component.ecosystem else None
    if descriptor.scope == MatchScope.NAME:
        return True
    if descriptor.scope == MatchScope.PRODUCT:
        return ecosystem is None
    if ecosystem is None:
        return False
    return not descriptor.ecosystems or ecosystem in descriptor.ecosystems


def _error_message(error: Exception) -> str:
    """Nur eigene Quellen-Meldungen im Wortlaut; alles andere könnte Interna enthalten."""
    if isinstance(error, SourceAccessError):
        return (str(error) or "Quelle nicht erreichbar")[:_MAX_MESSAGE_LENGTH]
    _logger.exception("Unerwarteter Fehler in einer Quelle")
    return f"Unerwarteter Fehler ({type(error).__name__})"


def _render_body(merged: MergedAdvisory, rationale: str) -> str:
    lines = [merged.details, "", "# Computation", rationale]
    if merged.references:
        lines += ["", "# References", *[f"- {url}" for url in merged.references]]
    return "\n".join(lines)


def _tags(hits: Sequence[_Hit]) -> list[str]:
    tags: list[str] = []
    for hit in hits:
        if hit.component.ecosystem:
            tags.append(hit.component.ecosystem.value)
        tags.append(hit.component.name)
    return list(dict.fromkeys(tags))


def _normalized_name(component: Component) -> str:
    ecosystem = component.ecosystem.value if component.ecosystem else None
    return normalize_package_name(ecosystem, component.name)


class _SourceCollector:
    """Fragt eine Quelle ab und liefert die passenden Treffer."""

    def __init__(self, matcher: ComponentMatcher) -> None:
        self._matcher = matcher

    def collect(
        self, source: VulnerabilitySource, api_key: str | None, components: Sequence[Component]
    ) -> list[_Hit]:
        descriptor = source.descriptor
        targets = [component for component in components if in_scope(descriptor, component)]
        if descriptor.kind == SourceKind.BULK:
            return self._from_bulk(cast(BulkSource, source), api_key, targets)
        return self._from_queries(cast(PackageQuerySource, source), api_key, targets)

    def _from_bulk(
        self, source: BulkSource, api_key: str | None, targets: Sequence[Component]
    ) -> list[_Hit]:
        if not targets:
            return []
        names = frozenset(_normalized_name(component) for component in targets)
        vulns = source.load(api_key, names)
        scope = source.descriptor.scope
        return [
            _Hit(component, vuln)
            for component in targets
            for vuln in vulns
            if self._matcher.matches(component, vuln, scope)
        ]

    def _from_queries(
        self, source: PackageQuerySource, api_key: str | None, targets: Sequence[Component]
    ) -> list[_Hit]:
        scope = source.descriptor.scope
        hits: list[_Hit] = []
        for component in targets:
            for vuln in source.query(component, api_key):
                # Paket-APIs gleichen die Version selbst ab; alles andere prüfen wir.
                if scope == MatchScope.PACKAGE or self._matcher.matches(component, vuln, scope):
                    hits.append(_Hit(component, vuln))
        return hits


class RunIngest:
    def __init__(
        self,
        uow: UnitOfWork,
        registry: SourceRegistry,
        matcher: ComponentMatcher,
        store: AdvisoryStore,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._registry = registry
        self._collector = _SourceCollector(matcher)
        self._store = store
        self._clock = clock

    def execute(self) -> IngestResult:
        components = [
            component
            for component in self._uow.components.list_all()
            if component.id is not None and component.application_id is not None
        ]
        results: list[SourceRunResult] = []
        hits: list[_Hit] = []
        for source in self._registry.all():
            result, source_hits = self._run_source(source, components)
            results.append(result)
            hits.extend(source_hits)
        found = self._persist(hits)
        self._uow.commit()
        return IngestResult(len(components), found, results)

    def _run_source(
        self, source: VulnerabilitySource, components: Sequence[Component]
    ) -> tuple[SourceRunResult, list[_Hit]]:
        setting = load_setting(self._uow, source.descriptor.key)
        status = source_status(source.descriptor, setting)
        if status != SourceStatus.READY:
            return self._finish(setting, RunStatus.SKIPPED, _SKIP_MESSAGES[status], None), []
        self._save(setting, RunStatus.RUNNING, "", setting.last_findings)
        try:
            hits = self._collector.collect(source, setting.api_key, components)
        except Exception as error:
            return self._finish(setting, RunStatus.ERROR, _error_message(error), None), []
        return self._finish(setting, RunStatus.OK, "", len(hits)), hits

    def _finish(
        self, setting: SourceSetting, status: RunStatus, message: str, findings: int | None
    ) -> SourceRunResult:
        self._save(setting, status, message, findings)
        return SourceRunResult(setting.source_key, status, findings or 0, message)

    def _save(
        self, setting: SourceSetting, status: RunStatus, message: str, findings: int | None
    ) -> None:
        setting.last_status = status
        setting.last_message = message
        setting.last_findings = findings
        setting.last_run_at = self._clock()
        self._uow.source_settings.save(setting)
        self._uow.commit()

    def _persist(self, hits: Sequence[_Hit]) -> int:
        groups: dict[str, list[_Hit]] = {}
        for hit in hits:
            groups.setdefault(advisory_key(hit.vuln)[0], []).append(hit)
        order = [*MERGE_PRECEDENCE, *(d.key for d in self._registry.descriptors())]
        return sum(self._persist_advisory(group, order) for group in groups.values())

    def _persist_advisory(self, hits: Sequence[_Hit], order: Sequence[str]) -> int:
        merged = merge_vulns([hit.vuln for hit in hits], order)
        risk = compute_risk_score(merged.cvss_base)
        advisory = Advisory(
            advisory_id=merged.advisory_id,
            cve_id=merged.cve_id,
            title=merged.title,
            description=merged.description,
            cvss_base=merged.cvss_base,
            fixed_version=merged.fixed_version,
            references=merged.references,
            okf_path="",
        )
        try:
            okf_path = self._store.save(
                advisory,
                tags=_tags(hits),
                sources=merged.sources,
                body=_render_body(merged, risk.rationale),
            )
        except ValueError:
            # Unzulässige ID aus einer Fremdquelle: verwerfen, Lauf geht weiter.
            return 0
        self._uow.advisories.upsert(replace(advisory, okf_path=okf_path))
        components = {hit.component.id: hit.component for hit in hits}
        for component in components.values():
            assert component.id is not None
            assert component.application_id is not None
            self._uow.findings.upsert(
                Finding(
                    advisory_id=merged.advisory_id,
                    component_id=component.id,
                    application_id=component.application_id,
                    found_version=component.version,
                    risk=risk,
                )
            )
        return len(components)


def run_ingest_job(
    uow_factory: UnitOfWorkFactory,
    registry: SourceRegistry,
    matcher: ComponentMatcher,
    store: AdvisoryStore,
    clock: Clock,
) -> IngestResult:
    """Führt einen Lauf mit eigener Unit of Work aus (für den Hintergrund-Thread)."""
    with uow_factory() as uow:
        return RunIngest(uow, registry, matcher, store, clock).execute()
