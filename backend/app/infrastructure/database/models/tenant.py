import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base


class TenantModel(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ruc: Mapped[str] = mapped_column(String(13), unique=True, nullable=False)
    razon_social: Mapped[str] = mapped_column(String(300), nullable=False)
    nombre_comercial: Mapped[str | None] = mapped_column(String(300), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="TRIAL")
    ambiente_sri: Mapped[str] = mapped_column(String(10), nullable=False, default="PRUEBAS")
    plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("planes.id"), nullable=True)
    comprobantes_mes_actual: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    settings: Mapped["TenantSettingsModel"] = relationship(back_populates="tenant", uselist=False)


class TenantSettingsModel(Base):
    __tablename__ = "tenant_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True,
    )
    logo_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color_primario: Mapped[str | None] = mapped_column(String(7), nullable=True)
    color_secundario: Mapped[str | None] = mapped_column(String(7), nullable=True)
    email_remitente: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nombre_remitente: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config_email: Mapped[dict] = mapped_column(JSONB, default={})
    campos_custom: Mapped[dict] = mapped_column(JSONB, default={})
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    tenant: Mapped["TenantModel"] = relationship(back_populates="settings")
