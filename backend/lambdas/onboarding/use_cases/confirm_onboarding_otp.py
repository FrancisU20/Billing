from __future__ import annotations

from dataclasses import dataclass

from lambdas.onboarding.domain.commands import ConfirmOnboardingOtpCommand
from lambdas.onboarding.domain.enterprise_lead import EnterpriseLead
from lambdas.onboarding.domain.errors import OnboardingPayloadMismatchError
from lambdas.onboarding.domain.events import EnterpriseLeadCreatedEvent
from lambdas.onboarding.domain.onboarding_verification import OnboardingVerification
from lambdas.onboarding.domain.repositories.i_identity_provider import IIdentityProvider
from lambdas.onboarding.domain.repositories.i_onboarding_verification_repository import (
    IOnboardingVerificationRepository,
)
from lambdas.onboarding.domain.repositories.i_plan_catalog import IPlanCatalog
from lambdas.onboarding.use_cases.payload_signature import onboarding_payload_hash
from lambdas.tenants.domain.commands import CreateTenantCommand
from lambdas.tenants.domain.errors import (
    TenantAccountAlreadyExistsError,
    TenantRucAlreadyExistsError,
)
from lambdas.tenants.domain.events import TenantCreatedEvent
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.dates import now_utc
from shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True)
class ConfirmOnboardingOtpResult:
    tenant: Tenant | None
    lead: EnterpriseLead | None
    verification: OnboardingVerification
    events: list[DomainEvent]


class ConfirmOnboardingOtpUseCase:
    def __init__(
        self,
        plan_catalog: IPlanCatalog,
        tenant_repo: ITenantRepository,
        verification_repo: IOnboardingVerificationRepository,
        identity_provider: IIdentityProvider,
    ) -> None:
        self._plan_catalog = plan_catalog
        self._tenant_repo = tenant_repo
        self._verification_repo = verification_repo
        self._identity_provider = identity_provider

    def execute(self, cmd: ConfirmOnboardingOtpCommand) -> ConfirmOnboardingOtpResult:
        verification = self._verification_repo.get_by_id(cmd.verification_id)
        verification.ensure_active()
        if not verification.verify(cmd.otp):
            try:
                verification.register_failed_attempt()
            finally:
                self._verification_repo.save_attempts(verification)

        if verification.payload_hash != onboarding_payload_hash(cmd):
            raise OnboardingPayloadMismatchError()

        plan = self._plan_catalog.get(cmd.plan_id)
        if plan.self_service != verification.self_service:
            raise OnboardingPayloadMismatchError()

        if plan.self_service:
            return self._register_tenant(
                cmd,
                verification,
                plan_id=plan.id,
                plan_limit_cycle=plan.limit_cycle,
                plan_is_free=plan.is_free,
            )
        return self._capture_lead(cmd, verification, plan_id=plan.id, plan_name=plan.name)

    def _register_tenant(
        self,
        cmd: ConfirmOnboardingOtpCommand,
        verification: OnboardingVerification,
        *,
        plan_id: str,
        plan_limit_cycle: str,
        plan_is_free: bool,
    ) -> ConfirmOnboardingOtpResult:
        if self._tenant_repo.get_by_ruc(cmd.ruc):
            raise TenantRucAlreadyExistsError()
        if self._identity_provider.email_exists(cmd.email):
            raise TenantAccountAlreadyExistsError()
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
                billing_cycle=cmd.billing_cycle,
                created_by="onboarding",
            ),
            plan_limit_cycle=plan_limit_cycle,
        )
        if not plan_is_free:
            # Netflix model: cycle starts at first payment, not at registration.
            tenant.plan_cycle_ends_at = None
            tenant.subscription_status = "pending_payment"
        # The certificate is uploaded later, after payment — see context/CERTIFICATES.md.
        tenant.onboarding_completed_at = now_utc()
        events = [
            TenantCreatedEvent(
                tenant_id=tenant.id,
                ruc=tenant.ruc,
                email=tenant.email,
                legal_rep_name=tenant.legal_rep_name,
            )
        ]
        return ConfirmOnboardingOtpResult(
            tenant=tenant,
            lead=None,
            verification=verification,
            events=events,
        )

    def _capture_lead(
        self,
        cmd: ConfirmOnboardingOtpCommand,
        verification: OnboardingVerification,
        *,
        plan_id: str,
        plan_name: str,
    ) -> ConfirmOnboardingOtpResult:
        lead = EnterpriseLead.create(cmd, plan_id=plan_id)
        events = [
            EnterpriseLeadCreatedEvent(
                lead_id=lead.id,
                ruc=lead.ruc,
                trade_name=lead.trade_name,
                email=lead.email,
                plan_id=lead.plan_id,
                plan_name=plan_name,
            )
        ]
        return ConfirmOnboardingOtpResult(
            tenant=None,
            lead=lead,
            verification=verification,
            events=events,
        )
