"""
Worker de consulta de autorización al SRI.
Triggered por: SQS sri-authorization-queue y EventBridge scheduler.
"""
from datetime import UTC, datetime

from aws_lambda_powertools import Logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums.estado_comprobante import EstadoComprobante
from app.infrastructure.database.connection import get_session_factory
from app.infrastructure.database.models.comprobante import SriSubmissionModel
from app.infrastructure.database.repositories.comprobante_repository import SqlAlchemyComprobanteRepository
from app.infrastructure.database.repositories.tenant_repository import SqlAlchemyTenantRepository
from app.infrastructure.queues.sqs_publisher import encolar_envio_email
from app.infrastructure.sri.soap_client import consultar_autorizacion
from app.infrastructure.storage.s3_storage import (
    descargar_documento,
    s3_key_xml_autorizado,
    subir_documento,
)
from app.shared.config import get_settings

logger = Logger(service="codelabs-billing-sri-retry")

MAX_RETRIES = 5


async def consultar_autorizacion_comprobante(
    comprobante_id: str,
    clave_acceso: str,
    ambiente: str,
) -> None:
    async with get_session_factory()() as session, session.begin():
        await _consultar(session, comprobante_id, clave_acceso, ambiente)


async def reintentar_pendientes() -> None:
    """Scheduler: consulta todos los comprobantes en RETRY_PENDING."""
    async with get_session_factory()() as session, session.begin():
        comp_repo = SqlAlchemyComprobanteRepository(session)
        pendientes = await comp_repo.list_retry_pending(limit=50)
        for comp in pendientes:
            if not comp.clave_acceso:
                continue

            tenant_repo = SqlAlchemyTenantRepository(session)
            tenant = await tenant_repo.get_by_id(comp.tenant_id)
            if tenant:
                ambiente = get_settings().effective_ambiente(tenant.ambiente_sri)
                await _consultar(session, str(comp.id), comp.clave_acceso, ambiente)


async def _consultar(
    session: AsyncSession,
    comprobante_id: str,
    clave_acceso: str,
    ambiente: str,
) -> None:

    comp_repo = SqlAlchemyComprobanteRepository(session)
    comp = await comp_repo.get_by_clave_acceso(clave_acceso)
    if not comp:
        logger.error("Comprobante no encontrado por clave de acceso", extra={"clave_acceso": clave_acceso})
        return

    respuesta = consultar_autorizacion(clave_acceso, ambiente)

    submission = SriSubmissionModel(
        comprobante_id=comp.id,
        tipo="AUTORIZACION",
        ambiente=ambiente,
        request_claveacceso=clave_acceso,
        response_estado=respuesta.estado,
        response_mensajes={"mensajes": respuesta.mensajes},
    )
    session.add(submission)

    logger.info("Respuesta SRI autorización", extra={
        "comprobante_id": comprobante_id,
        "estado": respuesta.estado,
        "numero_autorizacion": respuesta.numero_autorizacion,
    })

    if respuesta.estado == "AUTORIZADO":
        comp.numero_autorizacion = respuesta.numero_autorizacion
        comp.fecha_autorizacion = datetime.now(UTC)
        await session.flush()

        # Subir XML autorizado a S3 (con clave de autorización en el nombre)
        if comp.s3_key_xml_firmado:
            xml_firmado = descargar_documento(comp.s3_key_xml_firmado)
            s3_key = s3_key_xml_autorizado(str(comp.tenant_id), clave_acceso)
            subir_documento(xml_firmado, s3_key, "application/xml")
            comp.s3_key_xml_autorizado = s3_key

        await comp_repo.update_estado(comp.id, EstadoComprobante.AUTHORIZED)
        await comp_repo.update_estado(comp.id, EstadoComprobante.EMAIL_PENDING)
        await session.flush()
        encolar_envio_email(comprobante_id, str(comp.tenant_id))

    elif respuesta.estado == "NO AUTORIZADO":
        mensajes_str = [m["mensaje"] for m in respuesta.mensajes]
        comp.error_detalle = "; ".join(mensajes_str)
        await comp_repo.update_estado(
            comp.id, EstadoComprobante.NOT_AUTHORIZED,
            metadata={"mensajes": respuesta.mensajes},
        )

    else:
        # EN PROCESO o desconocido — reintento
        comp.increment_retry()
        if comp.retry_count >= MAX_RETRIES:
            await comp_repo.update_estado(comp.id, EstadoComprobante.MANUAL_REVIEW_REQUIRED)
        else:
            await comp_repo.update_estado(comp.id, EstadoComprobante.RETRY_PENDING)
