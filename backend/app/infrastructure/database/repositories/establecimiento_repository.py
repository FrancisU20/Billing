from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.establecimiento import (
    EstablecimientoModel,
    PuntoEmisionModel,
    SecuencialModel,
)

_ESTADO_ACTIVE = "ACTIVE"
_ESTADO_INACTIVE = "INACTIVE"


class EstablecimientoRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_by_tenant(self, tenant_id: UUID) -> list[EstablecimientoModel]:
        result = await self._session.execute(
            select(EstablecimientoModel)
            .where(EstablecimientoModel.tenant_id == tenant_id, EstablecimientoModel.estado == _ESTADO_ACTIVE)
            .order_by(EstablecimientoModel.codigo)
        )
        return list(result.scalars().all())

    async def get(self, tenant_id: UUID, codigo: str) -> EstablecimientoModel | None:
        result = await self._session.execute(
            select(EstablecimientoModel).where(
                EstablecimientoModel.tenant_id == tenant_id,
                EstablecimientoModel.codigo == codigo,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: UUID, codigo: str, direccion: str | None) -> EstablecimientoModel:
        model = EstablecimientoModel(tenant_id=tenant_id, codigo=codigo.zfill(3), direccion=direccion)
        self._session.add(model)
        await self._session.flush()
        return model

    async def delete(self, tenant_id: UUID, codigo: str) -> None:
        est = await self.get(tenant_id, codigo)
        if est:
            est.estado = _ESTADO_INACTIVE
            # Cascada: desactivar todos los puntos de emisión del establecimiento
            puntos = await self._session.execute(
                select(PuntoEmisionModel).where(PuntoEmisionModel.establecimiento_id == est.id)
            )
            for pto in puntos.scalars().all():
                pto.estado = _ESTADO_INACTIVE
            await self._session.flush()


class PuntoEmisionRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_by_establecimiento(self, establecimiento_id: UUID) -> list[PuntoEmisionModel]:
        result = await self._session.execute(
            select(PuntoEmisionModel)
            .where(
                PuntoEmisionModel.establecimiento_id == establecimiento_id,
                PuntoEmisionModel.estado == _ESTADO_ACTIVE,
            )
            .order_by(PuntoEmisionModel.codigo)
        )
        return list(result.scalars().all())

    async def get(self, establecimiento_id: UUID, codigo: str) -> PuntoEmisionModel | None:
        result = await self._session.execute(
            select(PuntoEmisionModel).where(
                PuntoEmisionModel.establecimiento_id == establecimiento_id,
                PuntoEmisionModel.codigo == codigo,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, establecimiento_id: UUID, codigo: str) -> PuntoEmisionModel:
        model = PuntoEmisionModel(establecimiento_id=establecimiento_id, codigo=codigo.zfill(3))
        self._session.add(model)
        await self._session.flush()
        return model

    async def delete(self, establecimiento_id: UUID, codigo: str) -> None:
        pto = await self.get(establecimiento_id, codigo)
        if pto:
            pto.estado = _ESTADO_INACTIVE
            await self._session.flush()


class SecuencialRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_or_create(self, punto_emision_id: UUID, tipo_comprobante: str) -> SecuencialModel:
        result = await self._session.execute(
            select(SecuencialModel).where(
                SecuencialModel.punto_emision_id == punto_emision_id,
                SecuencialModel.tipo_comprobante == tipo_comprobante,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            model = SecuencialModel(
                punto_emision_id=punto_emision_id,
                tipo_comprobante=tipo_comprobante,
                secuencial_actual=0,
            )
            self._session.add(model)
            await self._session.flush()
        return model

    async def next_secuencial(self, punto_emision_id: UUID, tipo_comprobante: str) -> str:
        """Incrementa y retorna el siguiente secuencial como string de 9 dígitos (con LOCK)."""
        # SELECT FOR UPDATE garantiza que dos Lambdas concurrentes no obtengan el mismo número
        result = await self._session.execute(
            select(SecuencialModel)
            .where(
                SecuencialModel.punto_emision_id == punto_emision_id,
                SecuencialModel.tipo_comprobante == tipo_comprobante,
            )
            .with_for_update()
        )
        model = result.scalar_one_or_none()
        if not model:
            model = SecuencialModel(
                punto_emision_id=punto_emision_id,
                tipo_comprobante=tipo_comprobante,
                secuencial_actual=0,
            )
            self._session.add(model)

        model.secuencial_actual += 1
        await self._session.flush()
        return str(model.secuencial_actual).zfill(9)

    async def list_by_punto_emision(self, punto_emision_id: UUID) -> list[SecuencialModel]:
        result = await self._session.execute(
            select(SecuencialModel).where(SecuencialModel.punto_emision_id == punto_emision_id)
        )
        return list(result.scalars().all())
