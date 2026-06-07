from __future__ import annotations

from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.domain.events.domain_event import DomainEvent


class DeleteTenantUseCase:
    def __init__(self, repo: ITenantRepository) -> None:
        self._repo = repo

    def execute(self, tenant_id: str, deleted_by: str) -> tuple[Tenant, list[DomainEvent]]:
        tenant = self._repo.get_by_id(tenant_id)
        tenant.soft_delete(deleted_by)
        return tenant, []
