"""SQLAlchemy-Modelle. Alembic importiert dieses Modul fuer --autogenerate."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.inventory import COMPONENT_NAME_MAX_LENGTH, COMPONENT_VERSION_MAX_LENGTH
from app.domain.sbom import SBOM_LABEL_MAX_LENGTH, SBOM_NAME_MAX_LENGTH, SBOM_SERIAL_MAX_LENGTH
from app.domain.vulnerability import (
    ADVISORY_ID_MAX_LENGTH,
    ADVISORY_TITLE_MAX_LENGTH,
    FIX_VERSION_MAX_LENGTH,
)
from app.infrastructure.database import Base


class ApplicationModel(Base):
    __tablename__ = "application"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(1000), default="")


class ComponentModel(Base):
    __tablename__ = "component"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"))
    name: Mapped[str] = mapped_column(String(COMPONENT_NAME_MAX_LENGTH))
    version: Mapped[str] = mapped_column(String(COMPONENT_VERSION_MAX_LENGTH))
    category: Mapped[str] = mapped_column(String(20))
    ecosystem: Mapped[str | None] = mapped_column(String(20), nullable=True)
    direct: Mapped[bool] = mapped_column(default=True)
    sbom_id: Mapped[int | None] = mapped_column(
        ForeignKey("sbom.id", name="fk_component_sbom"), nullable=True
    )
    checked: Mapped[bool] = mapped_column(default=True, server_default=true())


class SbomModel(Base):
    __tablename__ = "sbom"
    __table_args__ = (UniqueConstraint("application_id", "name", name="uq_sbom_application_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"))
    name: Mapped[str] = mapped_column(String(SBOM_NAME_MAX_LENGTH))


class SbomVersionModel(Base):
    __tablename__ = "sbom_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    sbom_id: Mapped[int] = mapped_column(ForeignKey("sbom.id"))
    label: Mapped[str] = mapped_column(String(SBOM_LABEL_MAX_LENGTH))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    serial_number: Mapped[str | None] = mapped_column(String(SBOM_SERIAL_MAX_LENGTH), nullable=True)
    is_current: Mapped[bool] = mapped_column(default=True)
    # Momentaufnahme der Komponenten dieser Version (Liste von Objekten)
    components: Mapped[list[dict[str, object]]] = mapped_column(JSON)


class AdvisoryModel(Base):
    __tablename__ = "advisory"

    advisory_id: Mapped[str] = mapped_column(String(ADVISORY_ID_MAX_LENGTH), primary_key=True)
    cve_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    okf_path: Mapped[str] = mapped_column(String(300))
    title: Mapped[str] = mapped_column(String(ADVISORY_TITLE_MAX_LENGTH))
    description: Mapped[str] = mapped_column(Text)
    cvss_score: Mapped[float | None] = mapped_column(nullable=True)
    epss_score: Mapped[float | None] = mapped_column(nullable=True)
    in_kev: Mapped[bool] = mapped_column(default=False)
    fix_version: Mapped[str | None] = mapped_column(String(FIX_VERSION_MAX_LENGTH), nullable=True)


class FindingModel(Base):
    __tablename__ = "finding"
    __table_args__ = (
        UniqueConstraint("advisory_id", "component_id", name="uq_finding_advisory_component"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    advisory_id: Mapped[str] = mapped_column(ForeignKey("advisory.advisory_id"))
    component_id: Mapped[int] = mapped_column(ForeignKey("component.id"))
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"))
    found_version: Mapped[str] = mapped_column(String(100))
    risk_score: Mapped[int] = mapped_column()
    risk_level: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="offen")
    comment: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class SourceSettingModel(Base):
    __tablename__ = "source_setting"

    source_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_message: Mapped[str] = mapped_column(Text, default="")
    last_findings: Mapped[int | None] = mapped_column(nullable=True)
