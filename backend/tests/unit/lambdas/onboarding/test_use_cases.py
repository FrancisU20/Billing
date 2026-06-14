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
from lambdas.tenants.domain.errors import TenantRucAlreadyExistsError
from lambdas.tenants.domain.events import TenantCreatedEvent
from shared.certificates.errors import CertificateInvalidError, CertificateRucMismatchError
from shared.certificates.metadata import CertificateMetadata
from tests.unit.support import FakeTenantRepository, make_tenant, tenant_payload


class FakeOnboardingPlanCatalog(IPlanCatalog):
    def __init__(
        self,
        *,
        exists: bool = True,
        active: bool = True,
        self_service: bool = True,
        limit_cycle: str = "month",
    ) -> None:
        self.exists = exists
        self.active = active
        self.self_service = self_service
        self.limit_cycle = limit_cycle
        self.checked_ids: list[str] = []

    def get(self, plan_id: str) -> PlanSummary:
        self.checked_ids.append(plan_id)
        if not self.exists:
            raise PlanNotFoundError()
        if not self.active:
            raise PlanNotActiveError()
        return PlanSummary(id=plan_id, self_service=self.self_service, limit_cycle=self.limit_cycle)


class FakeCertificateValidator:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def validate_base64(self, **kwargs: Any) -> CertificateMetadata:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return CertificateMetadata(
            subject_ruc=kwargs["expected_ruc"],
            expires_at=datetime.now(UTC) + timedelta(days=365),
            issuer="Security Data",
        )


def _request_command(**overrides: Any) -> RequestOnboardingOtpCommand:
    payload = tenant_payload()
    payload.update(overrides)
    payload.setdefault("certificate_b64", "base64-p12")
    payload.setdefault("cert_password", "secret")
    return RequestOnboardingOtpCommand(**payload)


class RequestOnboardingOtpUseCaseTests(unittest.TestCase):
    def test_self_service_validates_certificate_before_checking_ruc(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(self_service=True)
        validator = FakeCertificateValidator(error=CertificateRucMismatchError())

        with self.assertRaises(CertificateRucMismatchError):
            RequestOnboardingOtpUseCase(catalog, repo, validator).execute(_request_command())

        self.assertEqual(len(validator.calls), 1)
        self.assertEqual(repo.get_by_ruc_calls, [])

    def test_self_service_rejects_existing_ruc_after_certificate_is_valid(self) -> None:
        repo = FakeTenantRepository()
        repo.existing_by_ruc = make_tenant()
        catalog = FakeOnboardingPlanCatalog(self_service=True)
        validator = FakeCertificateValidator()

        with self.assertRaises(TenantRucAlreadyExistsError):
            RequestOnboardingOtpUseCase(catalog, repo, validator).execute(_request_command())

        self.assertEqual(len(validator.calls), 1)

    def test_self_service_without_certificate_raises_invalid(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(self_service=True)
        validator = FakeCertificateValidator()

        with self.assertRaises(CertificateInvalidError):
            RequestOnboardingOtpUseCase(catalog, repo, validator).execute(
                _request_command(certificate_b64=None, cert_password=None)
            )

        self.assertEqual(validator.calls, [])

    def test_self_service_creates_verification_and_otp_event(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(self_service=True)
        validator = FakeCertificateValidator()

        result = RequestOnboardingOtpUseCase(catalog, repo, validator).execute(_request_command())

        self.assertIsInstance(result.verification, OnboardingVerification)
        self.assertTrue(result.verification.self_service)
        self.assertEqual(len(result.events), 1)
        event = result.events[0]
        self.assertIsInstance(event, OnboardingOtpRequestedEvent)
        self.assertEqual(event.verification_id, result.verification.id)
        self.assertEqual(len(event.otp), 6)

    def test_enterprise_plan_skips_certificate_and_ruc_check(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(self_service=False)
        validator = FakeCertificateValidator()

        result = RequestOnboardingOtpUseCase(catalog, repo, validator).execute(
            _request_command(certificate_b64=None, cert_password=None)
        )

        self.assertFalse(result.verification.self_service)
        self.assertEqual(validator.calls, [])
        self.assertEqual(repo.get_by_ruc_calls, [])


def _confirm_command(**overrides: Any) -> ConfirmOnboardingOtpCommand:
    payload = tenant_payload()
    payload.update(overrides)
    payload.setdefault("verification_id", "verification-1")
    payload.setdefault("otp", "123456")
    payload.setdefault("certificate_b64", "base64-p12")
    payload.setdefault("cert_password", "secret")
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


class FakeCertificateStore:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, Any]] = []

    def put_certificate(self, **kwargs: Any) -> str:
        self.put_calls.append(kwargs)
        return "arn:aws:secretsmanager:sa-east-1:123:secret:/tenant/certificate"


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

    def test_self_service_creates_tenant_and_event(self) -> None:
        cmd = _confirm_command()
        verification = _verification_for(cmd)

        result = self._execute_with_verification(cmd, verification)

        self.assertIsNotNone(result.tenant)
        self.assertIsNone(result.lead)
        self.assertEqual(len(result.events), 1)
        self.assertIsInstance(result.events[0], TenantCreatedEvent)

    def test_enterprise_plan_captures_lead_without_certificate(self) -> None:
        cmd = _confirm_command(certificate_b64=None, cert_password=None)
        verification = _verification_for(cmd, self_service=False)

        result = self._execute_with_verification(
            cmd, verification, catalog=FakeOnboardingPlanCatalog(self_service=False)
        )

        self.assertIsNone(result.tenant)
        self.assertIsNotNone(result.lead)
        self.assertEqual(len(result.events), 1)
        self.assertIsInstance(result.events[0], EnterpriseLeadCreatedEvent)

    def _execute_with_verification(
        self,
        cmd: ConfirmOnboardingOtpCommand,
        verification: OnboardingVerification,
        *,
        repo: FakeTenantRepository | None = None,
        catalog: FakeOnboardingPlanCatalog | None = None,
        validator: FakeCertificateValidator | None = None,
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
            certificate_validator=validator or FakeCertificateValidator(),
            certificate_store=FakeCertificateStore(),
        )
        return use_case.execute(cmd)


if __name__ == "__main__":
    unittest.main()
