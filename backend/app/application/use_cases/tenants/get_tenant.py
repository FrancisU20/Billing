from uuid import UUID
from app.domain.entities.tenant import Tenant
from app.domain.repositories.tenant_repository import TenantRepository
from app.shared.exceptions import NotFoundError


class GetTenantUseCase:
    def __init__(self, tenant_repo: TenantRepository):
        self._repo = tenant_repo

    async def execute(self, tenant_id: UUID) -> Tenant:
        tenant = await self._repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant", str(tenant_id))
        return tenant


class ListTenantsUseCase:
    def __init__(self, tenant_repo: TenantRepository):
        self._repo = tenant_repo

    async def execute(self, offset: int = 0, limit: int = 50) -> list[Tenant]:
        return await self._repo.list_all(offset=offset, limit=limit)
