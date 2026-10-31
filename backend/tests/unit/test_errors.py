from app.domain.errors import DomainError, EntityNotFoundError


def test_not_found_error_names_entity_and_id() -> None:
    error = EntityNotFoundError("Bestellung", 42)

    assert isinstance(error, DomainError)
    assert str(error) == "Bestellung 42 wurde nicht gefunden"
    assert error.entity_id == 42
