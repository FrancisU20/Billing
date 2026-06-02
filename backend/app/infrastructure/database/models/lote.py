import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.connection import Base


class LoteModel(Base):
    __tablename__ = "lotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)  # CSV | EXCEL | API
    estado: Mapped[str] = mapped_column(String(30), default="UPLOADED")
    s3_key_original: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    validos: Mapped[int] = mapped_column(Integer, default=0)
    invalidos: Mapped[int] = mapped_column(Integer, default=0)
    procesados: Mapped[int] = mapped_column(Integer, default=0)
    autorizados: Mapped[int] = mapped_column(Integer, default=0)
    fallidos: Mapped[int] = mapped_column(Integer, default=0)
    errores_resumen: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
