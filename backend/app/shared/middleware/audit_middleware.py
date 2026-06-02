"""
Middleware de auditoría.
Registra operaciones críticas en la tabla audit_log.
Se usa explícitamente en los use cases — NO como middleware HTTP genérico,
porque necesita el contexto de la operación para ser útil.
"""
import uuid
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models.audit import AuditLogModel


async def log_audit(
    session: AsyncSession,
    operacion: str,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    entidad: str | None = None,
    entidad_id: UUID | None = None,
    ip: str | None = None,
    request_id: str | None = None,
    datos_antes: dict | None = None,
    datos_despues: dict | None = None,
) -> None:
    entry = AuditLogModel(
        tenant_id=tenant_id,
        user_id=user_id,
        operacion=operacion,
        entidad=entidad,
        entidad_id=entidad_id,
        ip=ip,
        request_id=request_id,
        datos_antes=datos_antes,
        datos_despues=datos_despues,
    )
    session.add(entry)
    # No hacemos flush aquí — el commit del bloque de transacción lo incluye
