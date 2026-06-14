from __future__ import annotations

"""Transactional persistence for OTP confirmation side effects.

The handler should not compose DynamoDB transaction dictionaries. This adapter keeps
the cross-aggregate transaction details in infra while the handler speaks in domain
terms: register tenant or capture Enterprise lead after consuming the verification.
"""

from lambdas._base.idempotency import IdempotencyContext
from lambdas.onboarding.domain.enterprise_lead import EnterpriseLead
from lambdas.onboarding.domain.errors import OnboardingOtpInvalidError
from lambdas.onboarding.domain.onboarding_verification import OnboardingVerification
from lambdas.onboarding.domain.repositories.i_enterprise_lead_repository import (
    IEnterpriseLeadRepository,
)
from lambdas.onboarding.domain.repositories.i_onboarding_verification_repository import (
    IOnboardingVerificationRepository,
)
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.db.transactions import ExtraTransactionConditionFailedError
from shared.domain.events.domain_event import DomainEvent


class DynamoOnboardingCommitRepository:
    def __init__(
        self,
        tenant_repo: ITenantRepository,
        lead_repo: IEnterpriseLeadRepository,
        verification_repo: IOnboardingVerificationRepository,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._lead_repo = lead_repo
        self._verification_repo = verification_repo

    def commit_tenant_registration(
        self,
        *,
        tenant: Tenant,
        verification: OnboardingVerification,
        events: list[DomainEvent],
        idempotency: IdempotencyContext,
        response: dict,
    ) -> None:
        try:
            self._tenant_repo.commit(
                tenant=tenant,
                user_id="onboarding",
                action="CREATE",
                events=events,
                idempotency=idempotency,
                response=response,
                extra_transact_items=[
                    self._verification_repo.mark_used_transact_item(verification)
                ],
            )
        except ExtraTransactionConditionFailedError as exc:
            raise OnboardingOtpInvalidError() from exc

    def commit_enterprise_lead(
        self,
        *,
        lead: EnterpriseLead,
        verification: OnboardingVerification,
        events: list[DomainEvent],
        idempotency: IdempotencyContext,
        response: dict,
    ) -> None:
        try:
            self._lead_repo.commit(
                lead=lead,
                events=events,
                idempotency=idempotency,
                response=response,
                extra_transact_items=[
                    self._verification_repo.mark_used_transact_item(verification)
                ],
            )
        except ExtraTransactionConditionFailedError as exc:
            raise OnboardingOtpInvalidError() from exc
