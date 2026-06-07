from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant


class GetTenantUseCase:
    def __init__(self, repo: ITenantRepository) -> None:
        self._repo = repo

    def execute(self, tenant_id: str) -> Tenant:
        return self._repo.get_by_id(tenant_id)
