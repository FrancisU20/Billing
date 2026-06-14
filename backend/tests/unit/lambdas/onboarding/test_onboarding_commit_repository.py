from __future__ import annotations

import unittest

from lambdas.onboarding.domain.errors import OnboardingOtpInvalidError
from lambdas.onboarding.infra.onboarding_commit_repository import DynamoOnboardingCommitRepository
from shared.db.transactions import ExtraTransactionConditionFailedError
from tests.unit.support import make_tenant


class FakeTenantRepository:
    def __init__(self, error: Exception | None = None) -> None:
        self.commit_calls: list[dict] = []
        self.error = error

    def commit(self, **kwargs) -> None:
        self.commit_calls.append(kwargs)
        if self.error:
            raise self.error


class FakeEnterpriseLeadRepository:
    def __init__(self, error: Exception | None = None) -> None:
        self.commit_calls: list[dict] = []
        self.error = error

    def commit(self, **kwargs) -> None:
        self.commit_calls.append(kwargs)
        if self.error:
            raise self.error


class FakeVerificationRepository:
    def __init__(self) -> None:
        self.mark_used_calls: list[object] = []

    def mark_used_transact_item(self, verification):
        self.mark_used_calls.append(verification)
        return {"Update": {"Key": {"id": verification.id}}}


class Verification:
    id = "verification-1"


class Lead:
    id = "lead-1"


class OnboardingCommitRepositoryTests(unittest.TestCase):
    def test_commit_tenant_registration_adds_verification_consumption_atomically(self) -> None:
        tenant_repo = FakeTenantRepository()
        lead_repo = FakeEnterpriseLeadRepository()
        verification_repo = FakeVerificationRepository()
        verification = Verification()
        idempotency = object()
        response = {"statusCode": 201}

        repo = DynamoOnboardingCommitRepository(tenant_repo, lead_repo, verification_repo)
        repo.commit_tenant_registration(
            tenant=make_tenant(),
            verification=verification,
            events=[],
            idempotency=idempotency,
            response=response,
        )

        self.assertEqual(verification_repo.mark_used_calls, [verification])
        self.assertEqual(len(tenant_repo.commit_calls), 1)
        self.assertEqual(
            tenant_repo.commit_calls[0]["extra_transact_items"],
            [{"Update": {"Key": {"id": "verification-1"}}}],
        )
        self.assertIs(tenant_repo.commit_calls[0]["idempotency"], idempotency)
        self.assertIs(tenant_repo.commit_calls[0]["response"], response)
        self.assertEqual(lead_repo.commit_calls, [])

    def test_tenant_extra_condition_failure_maps_to_invalid_otp(self) -> None:
        repo = DynamoOnboardingCommitRepository(
            FakeTenantRepository(error=ExtraTransactionConditionFailedError()),
            FakeEnterpriseLeadRepository(),
            FakeVerificationRepository(),
        )

        with self.assertRaises(OnboardingOtpInvalidError):
            repo.commit_tenant_registration(
                tenant=make_tenant(),
                verification=Verification(),
                events=[],
                idempotency=object(),
                response={"statusCode": 201},
            )

    def test_commit_enterprise_lead_adds_verification_consumption_atomically(self) -> None:
        tenant_repo = FakeTenantRepository()
        lead_repo = FakeEnterpriseLeadRepository()
        verification_repo = FakeVerificationRepository()
        verification = Verification()

        repo = DynamoOnboardingCommitRepository(tenant_repo, lead_repo, verification_repo)
        repo.commit_enterprise_lead(
            lead=Lead(),
            verification=verification,
            events=[],
            idempotency=object(),
            response={"statusCode": 202},
        )

        self.assertEqual(verification_repo.mark_used_calls, [verification])
        self.assertEqual(len(lead_repo.commit_calls), 1)
        self.assertEqual(
            lead_repo.commit_calls[0]["extra_transact_items"],
            [{"Update": {"Key": {"id": "verification-1"}}}],
        )
        self.assertEqual(tenant_repo.commit_calls, [])

    def test_enterprise_extra_condition_failure_maps_to_invalid_otp(self) -> None:
        repo = DynamoOnboardingCommitRepository(
            FakeTenantRepository(),
            FakeEnterpriseLeadRepository(error=ExtraTransactionConditionFailedError()),
            FakeVerificationRepository(),
        )

        with self.assertRaises(OnboardingOtpInvalidError):
            repo.commit_enterprise_lead(
                lead=Lead(),
                verification=Verification(),
                events=[],
                idempotency=object(),
                response={"statusCode": 202},
            )


if __name__ == "__main__":
    unittest.main()
