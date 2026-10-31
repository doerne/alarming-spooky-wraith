from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from app.application.unit_of_work import UnitOfWork, UnitOfWorkFactory


def get_unit_of_work(request: Request) -> Iterator[UnitOfWork]:
    """Die konkrete Factory setzt der Composition Root (app/main.py)."""
    factory: UnitOfWorkFactory = request.app.state.uow_factory
    with factory() as uow:
        yield uow


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]
