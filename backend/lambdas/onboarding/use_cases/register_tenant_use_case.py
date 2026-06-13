from __future__ import annotations

from dataclasses import dataclass

from lambdas.onboarding.domain.commands import RegisterTenantCommand
from lambdas.onboarding.domain.enterprise_lead import EnterpriseLead
from lambdas.onboarding.domain.events import EnterpriseLeadCreatedEvent
from lambdas.onboarding.domain.repositories.i_plan_catalog import IPlanCatalog
from lambdas.tenants.domain.commands import CreateTenantCommand
from lambdas.tenants.domain.errors import TenantRucAlreadyExistsError
from lambdas.tenants.domain.events import TenantCreatedEvent
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True)
class RegisterTenantResult:
    tenant: Tenant | None
    lead: EnterpriseLead | None
    events: list[DomainEvent]


class RegisterTenantUseCase:
    def __init__(self, plan_catalog: IPlanCatalog, tenant_repo: ITenantRepository) -> None:
        self._plan_catalog = plan_catalog
        self._tenant_repo = tenant_repo

    def execute(self, cmd: RegisterTenantCommand) -> RegisterTenantResult:
        plan = self._plan_catalog.get(cmd.plan_id)

        if plan.self_service:
            return self._register_tenant(cmd, plan_id=plan.id, plan_limit_cycle=plan.limit_cycle)
        return self._capture_lead(cmd, plan_id=plan.id)

    def _register_tenant(
        self, cmd: RegisterTenantCommand, *, plan_id: str, plan_limit_cycle: str
    ) -> RegisterTenantResult:
        if self._tenant_repo.get_by_ruc(cmd.ruc):
            raise TenantRucAlreadyExistsError()

        tenant = Tenant.create(
            CreateTenantCommand(
                ruc=cmd.ruc,
                trade_name=cmd.trade_name,
                legal_name=cmd.legal_name,
                legal_rep_name=cmd.legal_rep_name,
                email=cmd.email,
                phone=cmd.phone,
                address=cmd.address,
                accounting_required=cmd.accounting_required,
                plan_id=plan_id,
                created_by="onboarding",
            ),
            plan_limit_cycle=plan_limit_cycle,
        )
        events = [
            TenantCreatedEvent(
                tenant_id=tenant.id,
                ruc=tenant.ruc,
                email=tenant.email,
                legal_rep_name=tenant.legal_rep_name,
            )
        ]
        return RegisterTenantResult(tenant=tenant, lead=None, events=events)

    def _capture_lead(self, cmd: RegisterTenantCommand, *, plan_id: str) -> RegisterTenantResult:
        lead = EnterpriseLead.create(cmd, plan_id=plan_id)
        events = [
            EnterpriseLeadCreatedEvent(
                lead_id=lead.id,
                ruc=lead.ruc,
                trade_name=lead.trade_name,
                email=lead.email,
                plan_id=lead.plan_id,
            )
        ]
        return RegisterTenantResult(tenant=None, lead=lead, events=events)
