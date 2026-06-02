from dataclasses import dataclass

from app.domain.entities.tenant import Tenant
from app.domain.repositories.tenant_repository import TenantRepository
from app.shared.exceptions import DomainError


@dataclass
class CreateTenantCommand:
    ruc: str
    razon_social: str
    nombre_comercial: str | None = None
    ambiente_sri: str = "PRUEBAS"
    plan_id: str | None = None


class CreateTenantUseCase:
    def __init__(self, tenant_repo: TenantRepository):
        self._repo = tenant_repo

    async def execute(self, cmd: CreateTenantCommand) -> Tenant:
        existing = await self._repo.get_by_ruc(cmd.ruc)
        if existing:
            raise DomainError(f"Ya existe un tenant con RUC {cmd.ruc}", code="TENANT_ALREADY_EXISTS")

        tenant = Tenant(
            ruc=cmd.ruc,
            razon_social=cmd.razon_social,
            nombre_comercial=cmd.nombre_comercial,
            ambiente_sri=cmd.ambiente_sri,
        )
        return await self._repo.save(tenant)
