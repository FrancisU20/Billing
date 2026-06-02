from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.tenant import Tenant
from app.domain.enums.estado_tenant import EstadoTenant
from app.domain.repositories.tenant_repository import TenantRepository
from app.infrastructure.database.models.tenant import TenantModel


def _to_entity(model: TenantModel) -> Tenant:
    return Tenant(
        id=model.id,
        ruc=model.ruc,
        razon_social=model.razon_social,
        nombre_comercial=model.nombre_comercial,
        estado=EstadoTenant(model.estado),
        ambiente_sri=model.ambiente_sri,
        plan_id=model.plan_id,
        comprobantes_mes_actual=model.comprobantes_mes_actual,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_model(entity: Tenant) -> TenantModel:
    return TenantModel(
        id=entity.id,
        ruc=entity.ruc,
        razon_social=entity.razon_social,
        nombre_comercial=entity.nombre_comercial,
        estado=entity.estado,
        ambiente_sri=entity.ambiente_sri,
        plan_id=entity.plan_id,
        comprobantes_mes_actual=entity.comprobantes_mes_actual,
    )


class SqlAlchemyTenantRepository(TenantRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        result = await self._session.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_ruc(self, ruc: str) -> Tenant | None:
        result = await self._session.execute(
            select(TenantModel).where(TenantModel.ruc == ruc)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def save(self, tenant: Tenant) -> Tenant:
        result = await self._session.execute(
            select(TenantModel).where(TenantModel.id == tenant.id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.razon_social = tenant.razon_social
            existing.nombre_comercial = tenant.nombre_comercial
            existing.estado = tenant.estado
            existing.ambiente_sri = tenant.ambiente_sri
            existing.plan_id = tenant.plan_id
            existing.comprobantes_mes_actual = tenant.comprobantes_mes_actual
            await self._session.flush()
            return _to_entity(existing)
        model = _to_model(tenant)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_all(self, offset: int = 0, limit: int = 50) -> list[Tenant]:
        result = await self._session.execute(
            select(TenantModel).order_by(TenantModel.created_at.desc()).offset(offset).limit(limit)
        )
        return [_to_entity(m) for m in result.scalars().all()]
