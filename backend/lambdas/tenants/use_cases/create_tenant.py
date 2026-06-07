from __future__ import annotations

from lambdas.tenants.domain.commands import CreateTenantCommand
from lambdas.tenants.domain.errors import TenantRucAlreadyExistsError
from lambdas.tenants.domain.events import TenantCreatedEvent
from lambdas.tenants.domain.repositories.i_plan_catalog import IPlanCatalog
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.domain.events.domain_event import DomainEvent


class CreateTenantUseCase:
    def __init__(self, repo: ITenantRepository, plan_catalog: IPlanCatalog) -> None:
        self._repo = repo
        self._plan_catalog = plan_catalog

    def execute(self, cmd: CreateTenantCommand) -> tuple[Tenant, list[DomainEvent]]:
        self._plan_catalog.ensure_active(cmd.plan_id)

        if self._repo.get_by_ruc(cmd.ruc):
            raise TenantRucAlreadyExistsError()

        tenant = Tenant.create(cmd)
        events = [
            TenantCreatedEvent(
                tenant_id=tenant.id,
                ruc=tenant.ruc,
                email=tenant.email,
                legal_rep_name=tenant.legal_rep_name,
            )
        ]
        return tenant, events
