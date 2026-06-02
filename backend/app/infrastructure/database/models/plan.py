import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class PlanModel(Base):
    __tablename__ = "planes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    max_comprobantes_mes: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_usd: Mapped[float | None] = mapped_column(nullable=True)
    features: Mapped[dict] = mapped_column(JSONB, default={})
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
