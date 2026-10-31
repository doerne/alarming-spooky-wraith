from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import DomainError, EntityNotFoundError

# Neue fachliche Fehler hier auf einen HTTP-Status abbilden.
_STATUS_BY_ERROR: dict[type[DomainError], HTTPStatus] = {
    EntityNotFoundError: HTTPStatus.NOT_FOUND,
}


def _status_for(exc: Exception) -> HTTPStatus:
    for error_type in type(exc).__mro__:
        if error_type in _STATUS_BY_ERROR:
            return _STATUS_BY_ERROR[error_type]
    return HTTPStatus.BAD_REQUEST


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=_status_for(exc), content={"detail": str(exc)})


def register_error_handlers(app: FastAPI) -> None:
    """Übersetzt fachliche Fehler in HTTP-Statuscodes."""
    app.add_exception_handler(DomainError, _handle_domain_error)
