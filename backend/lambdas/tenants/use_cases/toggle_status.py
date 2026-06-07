from __future__ import annotations

from lambdas.tenants.domain.commands import ToggleStatusCommand
from lambdas.tenants.domain.enums import TenantStatus
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.domain.events.domain_event import DomainEvent
from shared.errors import ValidationError


class ToggleStatusUseCase:
    def __init__(self, repo: ITenantRepository) -> None:
        self._repo = repo

    def execute(self, cmd: ToggleStatusCommand) -> tuple[Tenant, list[DomainEvent]]:
        try:
            new_status = TenantStatus(cmd.new_status)
        except ValueError:
            raise ValidationError(f"Estado inválido: {cmd.new_status}")

        tenant = self._repo.get_by_id(cmd.tenant_id)
        tenant.change_status(new_status, cmd.updated_by)
        return tenant, []
