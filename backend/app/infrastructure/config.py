from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Liest Umgebungsvariablen. Das DB-Passwort kommt aus einem Docker Secret."""

    db_host: str = "db"
    db_port: int = 3306
    db_name: str = "appdb"
    db_user: str = "app"
    db_password_file: Path = Path("/run/secrets/db_password")
    database_url: str | None = None
    enable_docs: bool = False

    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        password = quote_plus(self.db_password_file.read_text(encoding="utf-8").strip())
        return (
            f"mariadb+pymysql://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
