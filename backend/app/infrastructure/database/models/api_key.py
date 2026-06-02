import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ARRAY, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.connection import Base


class ApiKeyModel(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, default=60)
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    ultimo_uso_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
