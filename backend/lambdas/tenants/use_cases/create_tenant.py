from __future__ import annotations
from shared.domain.events.domain_event import DomainEvent

from lambdas.tenants.domain.commands import CreateTenantCommand
from lambdas.tenants.domain.events import TenantCreatedEvent
from lambdas.tenants.domain.errors import TenantRucAlreadyExistsError
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant


class CreateTenantUseCase:
    def __init__(self, repo: ITenantRepository) -> None:
        self._repo = repo

    def execute(self, cmd: CreateTenantCommand) -> tuple[Tenant, list[DomainEvent]]:
        existing = self._repo.get_by_ruc(cmd.ruc)
        if existing:
            raise TenantRucAlreadyExistsError()

        tenant = Tenant.create(cmd)

        events = [TenantCreatedEvent(
            tenant_id        = tenant.id,
            ruc              = tenant.ruc,
            email            = tenant.email,
            nombre_rep_legal = tenant.nombre_rep_legal,
        )]
        return tenant, events
