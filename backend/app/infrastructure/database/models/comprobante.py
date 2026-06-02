import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, func, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.connection import Base


class ComprobanteModel(Base):
    __tablename__ = "comprobantes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "tipo", "establecimiento", "punto_emision", "secuencial", name="uq_comprobante_serie"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_comprobante_idempotency"),
        Index("idx_comprobantes_tenant_estado", "tenant_id", "estado"),
        Index("idx_comprobantes_clave_acceso", "clave_acceso"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    clave_acceso: Mapped[str | None] = mapped_column(String(49), unique=True, nullable=True)
    establecimiento: Mapped[str] = mapped_column(String(3), nullable=False)
    punto_emision: Mapped[str] = mapped_column(String(3), nullable=False)
    secuencial: Mapped[str | None] = mapped_column(String(9), nullable=True)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    datos: Mapped[dict] = mapped_column(JSONB, nullable=False)
    numero_autorizacion: Mapped[str | None] = mapped_column(String(49), nullable=True)
    fecha_autorizacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    s3_key_xml: Mapped[str | None] = mapped_column(String(500), nullable=True)
    s3_key_xml_firmado: Mapped[str | None] = mapped_column(String(500), nullable=True)
    s3_key_xml_autorizado: Mapped[str | None] = mapped_column(String(500), nullable=True)
    s3_key_pdf: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )


class ComprobanteStatusHistoryModel(Base):
    __tablename__ = "comprobante_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comprobante_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("comprobantes.id"), nullable=False)
    estado_anterior: Mapped[str | None] = mapped_column(String(40), nullable=True)
    estado_nuevo: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SriSubmissionModel(Base):
    __tablename__ = "sri_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comprobante_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("comprobantes.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # RECEPCION | AUTORIZACION
    ambiente: Mapped[str] = mapped_column(String(10), nullable=False)
    request_claveacceso: Mapped[str | None] = mapped_column(String(49), nullable=True)
    response_estado: Mapped[str | None] = mapped_column(String(30), nullable=True)
    response_mensajes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    duracion_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
