from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.tenant import Tenant
from app.domain.enums.estado_tenant import EstadoTenant
from app.domain.repositories.tenant_repository import TenantRepository
from app.shared.exceptions import DomainError, NotFoundError


@dataclass
class UpdateTenantCommand:
    tenant_id: UUID
    razon_social: str | None = None
    nombre_comercial: str | None = None
    ambiente_sri: str | None = None
    estado: str | None = None


class UpdateTenantUseCase:
    def __init__(self, tenant_repo: TenantRepository):
        self._repo = tenant_repo

    async def execute(self, cmd: UpdateTenantCommand) -> Tenant:
        tenant = await self._repo.get_by_id(cmd.tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", str(cmd.tenant_id))

        if cmd.estado:
            try:
                EstadoTenant(cmd.estado)
            except ValueError as exc:
                raise DomainError(f"Estado inválido: {cmd.estado}", code="INVALID_ESTADO") from exc
            tenant.estado = cmd.estado

        if cmd.razon_social:
            tenant.razon_social = cmd.razon_social
        if cmd.nombre_comercial is not None:
            tenant.nombre_comercial = cmd.nombre_comercial
        if cmd.ambiente_sri:
            if cmd.ambiente_sri not in ("PRUEBAS", "PRODUCCION"):
                raise DomainError("ambiente_sri debe ser PRUEBAS o PRODUCCION", code="INVALID_AMBIENTE")
            tenant.ambiente_sri = cmd.ambiente_sri

        return await self._repo.save(tenant)
