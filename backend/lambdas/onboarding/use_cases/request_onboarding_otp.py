from __future__ import annotations

from dataclasses import dataclass

from lambdas.onboarding.domain.commands import RequestOnboardingOtpCommand
from lambdas.onboarding.domain.events import OnboardingOtpRequestedEvent
from lambdas.onboarding.domain.onboarding_verification import (
    OnboardingVerification,
    generate_otp,
)
from lambdas.onboarding.domain.repositories.i_identity_provider import IIdentityProvider
from lambdas.onboarding.domain.repositories.i_plan_catalog import IPlanCatalog
from lambdas.onboarding.use_cases.payload_signature import onboarding_payload_hash
from lambdas.tenants.domain.errors import (
    TenantAccountAlreadyExistsError,
    TenantRucAlreadyExistsError,
)
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True)
class RequestOnboardingOtpResult:
    verification: OnboardingVerification
    events: list[DomainEvent]


class RequestOnboardingOtpUseCase:
    def __init__(
        self,
        plan_catalog: IPlanCatalog,
        tenant_repo: ITenantRepository,
        identity_provider: IIdentityProvider,
    ) -> None:
        self._plan_catalog = plan_catalog
        self._tenant_repo = tenant_repo
        self._identity_provider = identity_provider

    def execute(self, cmd: RequestOnboardingOtpCommand) -> RequestOnboardingOtpResult:
        plan = self._plan_catalog.get(cmd.plan_id)

        if plan.self_service:
            if self._tenant_repo.get_by_ruc(cmd.ruc):
                raise TenantRucAlreadyExistsError()
            if self._identity_provider.email_exists(cmd.email):
                raise TenantAccountAlreadyExistsError()

        otp = generate_otp()
        verification = OnboardingVerification.create(
            ruc=cmd.ruc,
            email=cmd.email,
            plan_id=cmd.plan_id,
            payload_hash=onboarding_payload_hash(cmd),
            self_service=plan.self_service,
            otp=otp,
        )
        events = [
            OnboardingOtpRequestedEvent(
                verification_id=verification.id,
                ruc=verification.ruc,
                email=verification.email,
                legal_rep_name=cmd.legal_rep_name,
                otp=otp,
                expires_at=verification.expires_at,
            )
        ]
        return RequestOnboardingOtpResult(verification=verification, events=events)
