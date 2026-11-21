"""Überführt Advisories, die sich als Alias einer anderen herausstellen, in die kanonische."""

from collections.abc import Sequence

from app.application.unit_of_work import UnitOfWork
from app.domain.ports import AdvisoryStore
from app.domain.vulnerability import Finding, FindingStatus

_COMMENT_SEPARATOR = "\n\n"


def _merged_comment(first: str, second: str) -> str:
    return _COMMENT_SEPARATOR.join(comment for comment in (first, second) if comment)


class AliasAbsorber:
    """Hängt Treffer einer Alias-Advisory um und entfernt sie. Commit macht der Aufrufer."""

    def __init__(self, uow: UnitOfWork, store: AdvisoryStore) -> None:
        self._uow = uow
        self._store = store

    def absorb(self, canonical_id: str, aliases: Sequence[str]) -> None:
        # Die kanonische ID ist (wieder) eigenständig, kein Alias mehr.
        self._uow.advisory_aliases.remove(canonical_id)
        for alias_id in aliases:
            self._record_alias(alias_id, canonical_id)
            if self._uow.advisories.find(alias_id) is not None:
                self._absorb_advisory(alias_id, canonical_id)

    def _record_alias(self, alias_id: str, canonical_id: str) -> None:
        # Ketten nachziehen: wer bisher auf den Alias zeigte, zeigt jetzt auf die kanonische ID.
        self._uow.advisory_aliases.repoint(alias_id, canonical_id)
        self._uow.advisory_aliases.save(alias_id, canonical_id)

    def _absorb_advisory(self, alias_id: str, canonical_id: str) -> None:
        canonical = {
            finding.component_id: finding
            for finding in self._uow.findings.list_for_advisory(canonical_id)
        }
        for finding in self._uow.findings.list_for_advisory(alias_id):
            self._move(finding, canonical.get(finding.component_id), canonical_id)
        # Treffer zuerst, dann die Advisory (Fremdschlüssel finding → advisory).
        self._uow.advisories.delete(alias_id)
        # Die Datei geht schon vor dem Commit; scheitert er, fehlt nur das File;
        # die Anzeige fällt dann auf die Beschreibung aus der DB zurück (wie beim Schreiben).
        self._store.delete(alias_id)

    def _move(self, finding: Finding, target: Finding | None, canonical_id: str) -> None:
        assert finding.id is not None
        if target is None:
            self._uow.findings.reassign(finding.id, canonical_id)
            return
        assert target.id is not None
        status = finding.status if target.status == FindingStatus.OPEN else target.status
        comment = _merged_comment(target.comment, finding.comment)
        self._uow.findings.save_triage(target.id, status, comment)
        self._uow.findings.delete(finding.id)
