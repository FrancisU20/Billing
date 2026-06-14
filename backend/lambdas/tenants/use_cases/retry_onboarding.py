from __future__ import annotations

from lambdas.tenants.domain.commands import RetryTenantOnboardingCommand
from lambdas.tenants.domain.events import TenantCreatedEvent
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.domain.events.domain_event import DomainEvent


class RetryTenantOnboardingUseCase:
    def __init__(self, repo: ITenantRepository) -> None:
        self._repo = repo

    def execute(self, cmd: RetryTenantOnboardingCommand) -> tuple[Tenant, list[DomainEvent]]:
        tenant = self._repo.get_by_id(cmd.tenant_id)
        return tenant, [
            TenantCreatedEvent(
                tenant_id=tenant.id,
                ruc=tenant.ruc,
                email=tenant.email,
                legal_rep_name=tenant.legal_rep_name,
            )
        ]
