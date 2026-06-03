from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.comprobante import Comprobante
from app.domain.enums.estado_comprobante import EstadoComprobante
from app.domain.enums.tipo_comprobante import TipoComprobante
from app.domain.repositories.comprobante_repository import ComprobanteRepository
from app.infrastructure.database.models.comprobante import ComprobanteModel, ComprobanteStatusHistoryModel


def _to_entity(m: ComprobanteModel) -> Comprobante:
    return Comprobante(
        id=m.id,
        tenant_id=m.tenant_id,
        tipo=TipoComprobante(m.tipo),
        clave_acceso=m.clave_acceso,
        establecimiento=m.establecimiento,
        punto_emision=m.punto_emision,
        secuencial=m.secuencial,
        estado=EstadoComprobante(m.estado),
        idempotency_key=m.idempotency_key,
        external_reference=m.external_reference,
        datos=m.datos,
        numero_autorizacion=m.numero_autorizacion,
        fecha_autorizacion=m.fecha_autorizacion,
        s3_key_xml=m.s3_key_xml,
        s3_key_xml_firmado=m.s3_key_xml_firmado,
        s3_key_xml_autorizado=m.s3_key_xml_autorizado,
        s3_key_pdf=m.s3_key_pdf,
        lote_id=m.lote_id,
        retry_count=m.retry_count,
        error_detalle=m.error_detalle,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyComprobanteRepository(ComprobanteRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, comprobante_id: UUID, tenant_id: UUID) -> Comprobante | None:
        result = await self._session.execute(
            select(ComprobanteModel).where(
                ComprobanteModel.id == comprobante_id,
                ComprobanteModel.tenant_id == tenant_id,
            )
        )
        m = result.scalar_one_or_none()
        return _to_entity(m) if m else None

    async def get_by_idempotency_key(self, tenant_id: UUID, key: str) -> Comprobante | None:
        result = await self._session.execute(
            select(ComprobanteModel).where(
                ComprobanteModel.tenant_id == tenant_id,
                ComprobanteModel.idempotency_key == key,
            )
        )
        m = result.scalar_one_or_none()
        return _to_entity(m) if m else None

    async def get_by_clave_acceso(self, clave_acceso: str) -> Comprobante | None:
        result = await self._session.execute(
            select(ComprobanteModel).where(ComprobanteModel.clave_acceso == clave_acceso)
        )
        m = result.scalar_one_or_none()
        return _to_entity(m) if m else None

    async def save(self, comprobante: Comprobante) -> Comprobante:
        result = await self._session.execute(
            select(ComprobanteModel).where(ComprobanteModel.id == comprobante.id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.estado = comprobante.estado
            existing.clave_acceso = comprobante.clave_acceso
            existing.secuencial = comprobante.secuencial
            existing.numero_autorizacion = comprobante.numero_autorizacion
            existing.fecha_autorizacion = comprobante.fecha_autorizacion
            existing.s3_key_xml = comprobante.s3_key_xml
            existing.s3_key_xml_firmado = comprobante.s3_key_xml_firmado
            existing.s3_key_xml_autorizado = comprobante.s3_key_xml_autorizado
            existing.s3_key_pdf = comprobante.s3_key_pdf
            existing.retry_count = comprobante.retry_count
            existing.error_detalle = comprobante.error_detalle
            await self._session.flush()
            return _to_entity(existing)

        model = ComprobanteModel(
            id=comprobante.id,
            tenant_id=comprobante.tenant_id,
            tipo=comprobante.tipo,
            clave_acceso=comprobante.clave_acceso,
            establecimiento=comprobante.establecimiento,
            punto_emision=comprobante.punto_emision,
            secuencial=comprobante.secuencial,
            estado=comprobante.estado,
            idempotency_key=comprobante.idempotency_key,
            external_reference=comprobante.external_reference,
            datos=comprobante.datos,
            lote_id=comprobante.lote_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def update_estado(
        self,
        comprobante_id: UUID,
        nuevo_estado: EstadoComprobante,
        metadata: dict | None = None,
    ) -> None:
        result = await self._session.execute(
            select(ComprobanteModel).where(ComprobanteModel.id == comprobante_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return

        estado_anterior = model.estado
        model.estado = nuevo_estado
        model.updated_at = datetime.now(UTC)

        history = ComprobanteStatusHistoryModel(
            comprobante_id=comprobante_id,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            metadata_=metadata or {},
        )
        self._session.add(history)
        await self._session.flush()

    async def list_retry_pending(
        self, tenant_id: UUID | None = None, limit: int = 100,
    ) -> list[Comprobante]:
        cutoff = datetime.now(UTC) - timedelta(minutes=2)
        q = select(ComprobanteModel).where(
            ComprobanteModel.estado == EstadoComprobante.RETRY_PENDING,
            ComprobanteModel.updated_at < cutoff,
            ComprobanteModel.retry_count < 5,
        )
        if tenant_id:
            q = q.where(ComprobanteModel.tenant_id == tenant_id)
        q = q.limit(limit)
        result = await self._session.execute(q)
        return [_to_entity(m) for m in result.scalars().all()]

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = 50,
        estado: str | None = None,
    ) -> tuple[list[Comprobante], int]:
        q = select(ComprobanteModel).where(ComprobanteModel.tenant_id == tenant_id)
        count_q = select(func.count()).select_from(ComprobanteModel).where(
            ComprobanteModel.tenant_id == tenant_id
        )

        if estado:
            q = q.where(ComprobanteModel.estado == estado)
            count_q = count_q.where(ComprobanteModel.estado == estado)

        total = (await self._session.execute(count_q)).scalar() or 0
        result = await self._session.execute(
            q.order_by(ComprobanteModel.created_at.desc()).offset(offset).limit(limit)
        )
        return [_to_entity(m) for m in result.scalars().all()], total
