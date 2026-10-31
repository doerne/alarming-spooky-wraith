"""In-Memory-Adapter für schnelle Tests ohne Datenbank.

Für jedes neue Repository hier ein In-Memory-Gegenstück anlegen und im
InMemoryUnitOfWork registrieren.
"""


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1
