class DomainError(Exception):
    """Basis für alle fachlichen Fehler. Eigene Fehler davon ableiten."""


class EntityNotFoundError(DomainError):
    def __init__(self, entity: str, entity_id: int | str) -> None:
        super().__init__(f"{entity} {entity_id} wurde nicht gefunden")
        self.entity = entity
        self.entity_id = entity_id


class SourceAccessError(DomainError):
    """Eine Quelle ist nicht erreichbar oder lehnt die Anfrage ab."""


class InvalidValueError(DomainError, ValueError):
    """Eine fachlich ungültige Eingabe (z. B. leerer API-Key)."""


class InvalidSbomError(InvalidValueError):
    """Die hochgeladene Datei ist keine verwertbare CycloneDX-SBOM."""


class ConflictError(DomainError):
    """Die Anfrage widerspricht dem aktuellen Zustand."""


class DuplicateSbomVersionError(ConflictError):
    def __init__(self, serial_number: str) -> None:
        super().__init__(f"Diese SBOM ({serial_number}) ist bereits die aktuelle Version")


class ComponentManagedBySbomError(ConflictError):
    def __init__(self, component_id: int) -> None:
        super().__init__(
            f"Komponente {component_id} stammt aus einer SBOM und kann nicht bearbeitet werden"
        )
