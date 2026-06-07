from __future__ import annotations
from shared.domain.events.domain_event import DomainEvent
from shared.errors import ValidationError

from lambdas.tenants.domain.commands import ToggleStatusCommand
from lambdas.tenants.domain.enums import EstadoTenant
from lambdas.tenants.domain.events import TenantStatusChangedEvent
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant


class ToggleStatusUseCase:
    def __init__(self, repo: ITenantRepository) -> None:
        self._repo = repo

    def execute(self, cmd: ToggleStatusCommand) -> tuple[Tenant, list[DomainEvent]]:
        try:
            nuevo_estado = EstadoTenant(cmd.nuevo_estado)
        except ValueError:
            raise ValidationError(f"Estado inválido: {cmd.nuevo_estado}")

        tenant = self._repo.get_by_id(cmd.tenant_id)
        tenant.cambiar_estado(nuevo_estado, cmd.updated_by)

        events = [TenantStatusChangedEvent(
            tenant_id    = tenant.id,
            nuevo_estado = nuevo_estado.value,
            updated_by   = cmd.updated_by,
        )]
        return tenant, events
