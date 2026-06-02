import uuid
from sqlalchemy import String, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.connection import Base


class EstablecimientoModel(Base):
    __tablename__ = "establecimientos"
    __table_args__ = (UniqueConstraint("tenant_id", "codigo", name="uq_establecimiento"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(3), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class PuntoEmisionModel(Base):
    __tablename__ = "puntos_emision"
    __table_args__ = (UniqueConstraint("establecimiento_id", "codigo", name="uq_punto_emision"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    establecimiento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("establecimientos.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(3), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class SecuencialModel(Base):
    __tablename__ = "secuenciales"
    __table_args__ = (UniqueConstraint("punto_emision_id", "tipo_comprobante", name="uq_secuencial"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    punto_emision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("puntos_emision.id"), nullable=False)
    tipo_comprobante: Mapped[str] = mapped_column(String(10), nullable=False)
    secuencial_actual: Mapped[int] = mapped_column(BigInteger, default=0)
