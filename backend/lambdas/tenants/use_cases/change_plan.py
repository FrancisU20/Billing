from __future__ import annotations

from lambdas.tenants.domain.commands import ChangeTenantPlanCommand
from lambdas.tenants.domain.errors import TenantPlanChangeNotAllowedError
from lambdas.tenants.domain.repositories.i_plan_catalog import IPlanCatalog
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.domain.events.domain_event import DomainEvent

_ELIGIBLE_STATUSES = {None, "pending_payment"}


class ChangePlanUseCase:
    """Lets a tenant confirm or change its plan before the first payment —
    between OTP confirmation and certificate upload. See context/ONBOARDING.md."""

    def __init__(self, repo: ITenantRepository, plan_catalog: IPlanCatalog) -> None:
        self._repo = repo
        self._plan_catalog = plan_catalog

    def execute(self, cmd: ChangeTenantPlanCommand) -> tuple[Tenant, list[DomainEvent]]:
        tenant = self._repo.get_by_id(cmd.tenant_id)
        if tenant.subscription_status not in _ELIGIBLE_STATUSES:
            raise TenantPlanChangeNotAllowedError()

        plan_info = self._plan_catalog.ensure_self_service_active(cmd.plan_id)
        tenant.confirm_plan_selection(
            plan_id=cmd.plan_id,
            plan_limit_cycle=plan_info.limit_cycle,
            plan_is_free=plan_info.is_free,
            billing_cycle=cmd.billing_cycle,
            updated_by=cmd.updated_by,
        )
        return tenant, []
