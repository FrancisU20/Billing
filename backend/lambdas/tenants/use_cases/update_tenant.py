from __future__ import annotations
from shared.domain.events.domain_event import DomainEvent

from lambdas.tenants.domain.commands import UpdateTenantCommand
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant


class UpdateTenantUseCase:
    def __init__(self, repo: ITenantRepository) -> None:
        self._repo = repo

    def execute(self, cmd: UpdateTenantCommand) -> tuple[Tenant, list[DomainEvent]]:
        tenant = self._repo.get_by_id(cmd.tenant_id)
        tenant.update(cmd)
        return tenant, []
