from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from typing import Any

from lambdas.onboarding.domain.commands import (
    ConfirmOnboardingOtpCommand,
    RequestOnboardingOtpCommand,
)
from lambdas.onboarding.domain.errors import (
    OnboardingOtpAttemptsExceededError,
    OnboardingOtpExpiredError,
    OnboardingOtpInvalidError,
    OnboardingPayloadMismatchError,
    PlanNotActiveError,
    PlanNotFoundError,
)
from lambdas.onboarding.domain.events import EnterpriseLeadCreatedEvent, OnboardingOtpRequestedEvent
from lambdas.onboarding.domain.onboarding_verification import OnboardingVerification
from lambdas.onboarding.domain.repositories.i_plan_catalog import IPlanCatalog, PlanSummary
from lambdas.onboarding.use_cases.confirm_onboarding_otp import ConfirmOnboardingOtpUseCase
from lambdas.onboarding.use_cases.payload_signature import onboarding_payload_hash
from lambdas.onboarding.use_cases.request_onboarding_otp import RequestOnboardingOtpUseCase
from lambdas.tenants.domain.errors import (
    TenantAccountAlreadyExistsError,
    TenantRucAlreadyExistsError,
)
from lambdas.tenants.domain.events import TenantCreatedEvent
from tests.unit.support import FakeTenantRepository, make_tenant, tenant_payload


class FakeOnboardingPlanCatalog(IPlanCatalog):
    def __init__(
        self,
        *,
        exists: bool = True,
        active: bool = True,
        self_service: bool = True,
        limit_cycle: str = "month",
        is_free: bool = True,
        name: str = "Corporativo",
    ) -> None:
        self.exists = exists
        self.active = active
        self.self_service = self_service
        self.limit_cycle = limit_cycle
        self.is_free = is_free
        self.name = name
        self.checked_ids: list[str] = []

    def get(self, plan_id: str) -> PlanSummary:
        self.checked_ids.append(plan_id)
        if not self.exists:
            raise PlanNotFoundError()
        if not self.active:
            raise PlanNotActiveError()
        return PlanSummary(
            id=plan_id,
            self_service=self.self_service,
            limit_cycle=self.limit_cycle,
            is_free=self.is_free,
            name=self.name,
        )


class FakeIdentityProvider:
    def __init__(self, *, exists: bool = False) -> None:
        self.exists = exists
        self.checked_emails: list[str] = []

    def email_exists(self, email: str) -> bool:
        self.checked_emails.append(email)
        return self.exists


def _request_command(**overrides: Any) -> RequestOnboardingOtpCommand:
    payload = tenant_payload()
    payload.update(overrides)
    return RequestOnboardingOtpCommand(**payload)


class RequestOnboardingOtpUseCaseTests(unittest.TestCase):
    def test_self_service_rejects_existing_ruc(self) -> None:
        repo = FakeTenantRepository()
        repo.existing_by_ruc = make_tenant()
        catalog = FakeOnboardingPlanCatalog(self_service=True)

        with self.assertRaises(TenantRucAlreadyExistsError):
            RequestOnboardingOtpUseCase(catalog, repo, FakeIdentityProvider()).execute(
                _request_command()
            )

    def test_self_service_rejects_existing_email_in_cognito(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(self_service=True)
        identity_provider = FakeIdentityProvider(exists=True)

        with self.assertRaises(TenantAccountAlreadyExistsError):
            RequestOnboardingOtpUseCase(catalog, repo, identity_provider).execute(
                _request_command()
            )

        self.assertEqual(len(identity_provider.checked_emails), 1)

    def test_self_service_creates_verification_and_otp_event(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(self_service=True)

        result = RequestOnboardingOtpUseCase(catalog, repo, FakeIdentityProvider()).execute(
            _request_command()
        )

        self.assertIsInstance(result.verification, OnboardingVerification)
        self.assertTrue(result.verification.self_service)
        self.assertEqual(len(result.events), 1)
        event = result.events[0]
        self.assertIsInstance(event, OnboardingOtpRequestedEvent)
        self.assertEqual(event.verification_id, result.verification.id)
        self.assertEqual(len(event.otp), 6)

    def test_enterprise_plan_skips_ruc_and_email_check(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(self_service=False)
        identity_provider = FakeIdentityProvider()

        result = RequestOnboardingOtpUseCase(catalog, repo, identity_provider).execute(
            _request_command()
        )

        self.assertFalse(result.verification.self_service)
        self.assertEqual(repo.get_by_ruc_calls, [])
        self.assertEqual(identity_provider.checked_emails, [])


def _confirm_command(**overrides: Any) -> ConfirmOnboardingOtpCommand:
    payload = tenant_payload()
    payload.update(overrides)
    payload.setdefault("verification_id", "verification-1")
    payload.setdefault("otp", "123456")
    return ConfirmOnboardingOtpCommand(**payload)


def _verification_for(
    cmd: ConfirmOnboardingOtpCommand, *, self_service: bool = True
) -> OnboardingVerification:
    verification = OnboardingVerification.create(
        ruc=cmd.ruc,
        email=cmd.email,
        plan_id=cmd.plan_id,
        payload_hash=onboarding_payload_hash(cmd),
        self_service=self_service,
        otp=cmd.otp,
    )
    verification.id = cmd.verification_id
    return verification


class ConfirmOnboardingOtpUseCaseTests(unittest.TestCase):
    def test_invalid_otp_raises_and_registers_attempt(self) -> None:
        import dataclasses

        cmd = _confirm_command()
        verification = _verification_for(cmd)
        wrong_otp_cmd = dataclasses.replace(cmd, otp="000000")

        with self.assertRaises(OnboardingOtpInvalidError):
            self._execute_with_verification(wrong_otp_cmd, verification)

        self.assertEqual(verification.attempts, 1)

    def test_expired_otp_raises_expired(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd)
        verification.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        with self.assertRaises(OnboardingOtpExpiredError):
            self._execute_with_verification(cmd, verification)

    def test_attempts_exceeded_raises(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd)
        verification.attempts = verification.max_attempts

        with self.assertRaises(OnboardingOtpAttemptsExceededError):
            self._execute_with_verification(cmd, verification)

    def test_payload_mismatch_raises(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd)
        tampered = _confirm_command(trade_name="Otra Empresa S.A.")

        with self.assertRaises(OnboardingPayloadMismatchError):
            self._execute_with_verification(tampered, verification)

    def test_self_service_mismatch_raises(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd, self_service=False)

        with self.assertRaises(OnboardingPayloadMismatchError):
            self._execute_with_verification(
                cmd, verification, catalog=FakeOnboardingPlanCatalog(self_service=True)
            )

    def test_self_service_rejects_already_registered_ruc(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd)
        repo = FakeTenantRepository()
        repo.existing_by_ruc = make_tenant()

        with self.assertRaises(TenantRucAlreadyExistsError):
            self._execute_with_verification(cmd, verification, repo=repo)

    def test_self_service_rejects_existing_email_in_cognito(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd)
        identity_provider = FakeIdentityProvider(exists=True)

        with self.assertRaises(TenantAccountAlreadyExistsError):
            self._execute_with_verification(cmd, verification, identity_provider=identity_provider)

    def test_self_service_creates_tenant_and_event(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd)

        result = self._execute_with_verification(cmd, verification)

        self.assertIsNotNone(result.tenant)
        self.assertIsNone(result.lead)
        self.assertIsNotNone(result.tenant.onboarding_completed_at)
        self.assertIsNone(result.tenant.certificate_secret_arn)
        self.assertEqual(len(result.events), 1)
        self.assertIsInstance(result.events[0], TenantCreatedEvent)

    def test_free_plan_tenant_has_no_pending_payment_status(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd)

        result = self._execute_with_verification(
            cmd, verification, catalog=FakeOnboardingPlanCatalog(is_free=True)
        )

        self.assertIsNone(result.tenant.subscription_status)
        self.assertIsNotNone(result.tenant.plan_cycle_ends_at)

    def test_paid_plan_tenant_gets_pending_payment_and_no_cycle_end(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd)

        result = self._execute_with_verification(
            cmd, verification, catalog=FakeOnboardingPlanCatalog(is_free=False)
        )

        self.assertEqual(result.tenant.subscription_status, "pending_payment")
        self.assertIsNone(result.tenant.plan_cycle_ends_at)

    def test_enterprise_plan_captures_lead(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd, self_service=False)

        result = self._execute_with_verification(
            cmd, verification, catalog=FakeOnboardingPlanCatalog(self_service=False)
        )

        self.assertIsNone(result.tenant)
        self.assertIsNotNone(result.lead)
        self.assertEqual(len(result.events), 1)
        self.assertIsInstance(result.events[0], EnterpriseLeadCreatedEvent)
        self.assertEqual(result.events[0].plan_name, "Corporativo")

    def _execute_with_verification(
        self,
        cmd: ConfirmOnboardingOtpCommand,
        verification: OnboardingVerification,
        *,
        repo: FakeTenantRepository | None = None,
        catalog: FakeOnboardingPlanCatalog | None = None,
        identity_provider: FakeIdentityProvider | None = None,
    ):
        class _FakeVerificationRepo:
            def __init__(self, item: OnboardingVerification) -> None:
                self.item = item
                self.save_attempts_calls: list[Any] = []

            def get_by_id(self, verification_id: str) -> OnboardingVerification:
                return self.item

            def save_attempts(self, verification: OnboardingVerification) -> None:
                self.save_attempts_calls.append(verification)

        use_case = ConfirmOnboardingOtpUseCase(
            catalog or FakeOnboardingPlanCatalog(self_service=True),
            repo or FakeTenantRepository(),
            verification_repo=_FakeVerificationRepo(verification),
            identity_provider=identity_provider or FakeIdentityProvider(),
        )
        return use_case.execute(cmd)


if __name__ == "__main__":
    unittest.main()
