from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from lambdas.onboarding.domain.commands import ConfirmOnboardingOtpCommand
from lambdas.onboarding.domain.enterprise_lead import EnterpriseLead
from lambdas.onboarding.domain.errors import OnboardingPayloadMismatchError
from lambdas.onboarding.domain.events import EnterpriseLeadCreatedEvent
from lambdas.onboarding.domain.onboarding_verification import OnboardingVerification
from lambdas.onboarding.domain.repositories.i_onboarding_verification_repository import (
    IOnboardingVerificationRepository,
)
from lambdas.onboarding.domain.repositories.i_plan_catalog import IPlanCatalog
from lambdas.onboarding.use_cases.payload_signature import onboarding_payload_hash
from lambdas.tenants.domain.commands import CreateTenantCommand
from lambdas.tenants.domain.errors import TenantRucAlreadyExistsError
from lambdas.tenants.domain.events import TenantCreatedEvent
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.certificates.errors import CertificateInvalidError
from shared.certificates.store import CertificateStore
from shared.certificates.validator import CertificateValidator
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
        certificate_validator: CertificateValidator,
        certificate_store: CertificateStore,
    ) -> None:
        self._plan_catalog = plan_catalog
        self._tenant_repo = tenant_repo
        self._verification_repo = verification_repo
        self._certificate_validator = certificate_validator
        self._certificate_store = certificate_store

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
            )
        return self._capture_lead(cmd, verification, plan_id=plan.id)

    def _register_tenant(
        self,
        cmd: ConfirmOnboardingOtpCommand,
        verification: OnboardingVerification,
        *,
        plan_id: str,
        plan_limit_cycle: str,
    ) -> ConfirmOnboardingOtpResult:
        if not cmd.certificate_b64 or not cmd.cert_password:
            raise CertificateInvalidError("certificado requerido para self-service")

        metadata = self._certificate_validator.validate_base64(
            certificate_b64=cmd.certificate_b64,
            password=cmd.cert_password,
            expected_ruc=cmd.ruc,
        )
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
        secret_arn = self._certificate_store.put_certificate(
            tenant_id=tenant.id,
            certificate_b64=cmd.certificate_b64,
            password=cmd.cert_password,
        )
        tenant.attach_certificate(
            metadata,
            secret_arn=secret_arn,
            uploaded_at=datetime.now(UTC),
            updated_by="onboarding",
            complete_onboarding=True,
            touch_entity=False,
        )
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
    ) -> ConfirmOnboardingOtpResult:
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
        return ConfirmOnboardingOtpResult(
            tenant=None,
            lead=lead,
            verification=verification,
            events=events,
        )
