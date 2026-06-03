from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.domain.entities.comprobante import Comprobante
from app.domain.enums.estado_comprobante import EstadoComprobante
from app.domain.repositories.comprobante_repository import ComprobanteRepository
from app.infrastructure.queues.sqs_publisher import (
    encolar_consulta_autorizacion,
    encolar_envio_email,
    encolar_procesamiento,
)
from app.shared.exceptions import DomainError, NotFoundError

TipoReintento = Literal["REENVIAR_SRI", "RECONSULTAR_AUTORIZACION", "REENVIAR_EMAIL"]

REINTENTOS_PERMITIDOS: dict[TipoReintento, set[EstadoComprobante]] = {
    "REENVIAR_SRI": {
        EstadoComprobante.RETURNED_BY_SRI,
        EstadoComprobante.FAILED,
        EstadoComprobante.VALIDATION_FAILED,
    },
    "RECONSULTAR_AUTORIZACION": {
        EstadoComprobante.NOT_AUTHORIZED,
        EstadoComprobante.RETRY_PENDING,
        EstadoComprobante.MANUAL_REVIEW_REQUIRED,
        EstadoComprobante.PENDING_AUTHORIZATION,
    },
    "REENVIAR_EMAIL": {
        EstadoComprobante.EMAIL_FAILED,
        EstadoComprobante.AUTHORIZED,
        EstadoComprobante.EMAIL_SENT,
    },
}


@dataclass
class RetryComprobanteCommand:
    comprobante_id: UUID
    tenant_id: UUID
    tipo: TipoReintento
    ambiente: str = "PRUEBAS"


class RetryComprobanteUseCase:
    def __init__(self, comprobante_repo: ComprobanteRepository):
        self._repo = comprobante_repo

    async def execute(self, cmd: RetryComprobanteCommand) -> Comprobante:
        comprobante = await self._repo.get_by_id(cmd.comprobante_id, cmd.tenant_id)
        if not comprobante:
            raise NotFoundError("Comprobante", str(cmd.comprobante_id))

        estados_permitidos = REINTENTOS_PERMITIDOS.get(cmd.tipo, set())
        if comprobante.estado not in estados_permitidos:
            raise DomainError(
                f"No se puede hacer '{cmd.tipo}' desde el estado '{comprobante.estado}'",
                code="INVALID_RETRY",
            )

        if cmd.tipo == "REENVIAR_SRI":
            await self._repo.update_estado(comprobante.id, EstadoComprobante.QUEUED)
            encolar_procesamiento(str(comprobante.id), str(cmd.tenant_id))

        elif cmd.tipo == "RECONSULTAR_AUTORIZACION":
            await self._repo.update_estado(comprobante.id, EstadoComprobante.PENDING_AUTHORIZATION)
            if comprobante.clave_acceso:
                encolar_consulta_autorizacion(
                    str(comprobante.id), comprobante.clave_acceso, cmd.ambiente
                )

        elif cmd.tipo == "REENVIAR_EMAIL":
            await self._repo.update_estado(comprobante.id, EstadoComprobante.EMAIL_PENDING)
            encolar_envio_email(str(comprobante.id), str(cmd.tenant_id))

        return await self._repo.get_by_id(cmd.comprobante_id, cmd.tenant_id)
