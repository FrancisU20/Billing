from dataclasses import dataclass
from uuid import UUID

from app.application.schemas.factura import DatosFactura
from app.domain.entities.comprobante import Comprobante
from app.domain.enums.estado_comprobante import EstadoComprobante
from app.domain.enums.tipo_comprobante import TipoComprobante
from app.domain.repositories.comprobante_repository import ComprobanteRepository
from app.domain.repositories.tenant_repository import TenantRepository
from app.infrastructure.queues.sqs_publisher import encolar_procesamiento
from app.shared.exceptions import (
    DomainError,
    TenantNotActiveError,
)


@dataclass
class CreateComprobanteCommand:
    tenant_id: UUID
    tipo: str
    establecimiento: str
    punto_emision: str
    secuencial: str
    datos: dict
    idempotency_key: str | None = None
    external_reference: str | None = None
    lote_id: UUID | None = None


class CreateComprobanteUseCase:
    def __init__(
        self,
        comprobante_repo: ComprobanteRepository,
        tenant_repo: TenantRepository,
    ):
        self._comp_repo = comprobante_repo
        self._tenant_repo = tenant_repo

    async def execute(self, cmd: CreateComprobanteCommand) -> Comprobante:
        # 1. Verificar idempotency
        if cmd.idempotency_key:
            existing = await self._comp_repo.get_by_idempotency_key(
                cmd.tenant_id, cmd.idempotency_key
            )
            if existing:
                return existing

        # 2. Verificar tenant
        tenant = await self._tenant_repo.get_by_id(cmd.tenant_id)
        if not tenant:
            raise DomainError("Tenant no encontrado", code="NOT_FOUND")
        if not tenant.can_emit():
            raise TenantNotActiveError(str(cmd.tenant_id), tenant.estado)

        # 3. Validar datos según tipo de comprobante
        if cmd.tipo == TipoComprobante.FACTURA:
            DatosFactura(**cmd.datos)  # lanza ValidationError si es inválido

        # 4. Crear comprobante
        comprobante = Comprobante(
            tenant_id=cmd.tenant_id,
            tipo=cmd.tipo,
            establecimiento=cmd.establecimiento,
            punto_emision=cmd.punto_emision,
            secuencial=cmd.secuencial,
            datos=cmd.datos,
            idempotency_key=cmd.idempotency_key,
            external_reference=cmd.external_reference,
            lote_id=cmd.lote_id,
        )
        comprobante.transition_to(EstadoComprobante.PENDING_VALIDATION)
        comprobante.transition_to(EstadoComprobante.QUEUED)
        saved = await self._comp_repo.save(comprobante)

        # 5. Encolar para procesamiento asíncrono
        encolar_procesamiento(str(saved.id), str(cmd.tenant_id))

        return saved
