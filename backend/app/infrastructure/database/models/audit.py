import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.connection import Base


class AuditLogModel(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_tenant_operacion", "tenant_id", "operacion", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    operacion: Mapped[str] = mapped_column(String(100), nullable=False)
    entidad: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entidad_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    datos_antes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    datos_despues: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
