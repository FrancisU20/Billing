import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class EmailDispatchModel(Base):
    __tablename__ = "email_dispatches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comprobante_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("comprobantes.id"), nullable=False)
    proveedor: Mapped[str | None] = mapped_column(String(30), nullable=True)
    destinatario: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)  # RECEPTOR | COPIA | REENVIO
    estado: Mapped[str] = mapped_column(String(20), default="PENDING")
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    error_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enviado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
