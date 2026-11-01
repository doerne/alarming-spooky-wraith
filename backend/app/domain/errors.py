class DomainError(Exception):
    """Basis für alle fachlichen Fehler. Eigene Fehler davon ableiten."""


class EntityNotFoundError(DomainError):
    def __init__(self, entity: str, entity_id: int | str) -> None:
        super().__init__(f"{entity} {entity_id} wurde nicht gefunden")
        self.entity = entity
        self.entity_id = entity_id


class SourceAccessError(DomainError):
    """Eine Quelle ist nicht erreichbar oder lehnt die Anfrage ab."""
