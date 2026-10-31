"""SQLAlchemy-Modelle. Alembic importiert dieses Modul fuer --autogenerate."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

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
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(20))
    ecosystem: Mapped[str | None] = mapped_column(String(20), nullable=True)
    direct: Mapped[bool] = mapped_column(default=True)


class AdvisoryModel(Base):
    __tablename__ = "advisory"

    advisory_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    cve_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    okf_path: Mapped[str] = mapped_column(String(300))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    cvss_score: Mapped[float | None] = mapped_column(nullable=True)
    epss_score: Mapped[float | None] = mapped_column(nullable=True)
    in_kev: Mapped[bool] = mapped_column(default=False)
    fix_version: Mapped[str | None] = mapped_column(String(100), nullable=True)


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
