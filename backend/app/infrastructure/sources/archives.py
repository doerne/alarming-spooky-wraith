"""Zip-Archive aus dem Cache sicher öffnen und lesen."""

import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.domain.errors import SourceAccessError


@contextmanager
def open_archive(path: Path, source_name: str) -> Iterator[zipfile.ZipFile]:
    try:
        with zipfile.ZipFile(path) as archive:
            yield archive
    except zipfile.BadZipFile as error:
        raise SourceAccessError(f"{source_name}: Abzug ist beschädigt") from error
