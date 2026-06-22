from __future__ import annotations

import unittest
from types import SimpleNamespace

from botocore.exceptions import ClientError

from lambdas.onboarding.domain.commands import ConfirmOnboardingOtpCommand
from lambdas.onboarding.domain.enterprise_lead import EnterpriseLead
from lambdas.onboarding.infra.enterprise_lead_repository import DynamoEnterpriseLeadRepository
from shared.db.transactions import ExtraTransactionConditionFailedError
from shared.errors import DatabaseError
from tests.unit.support import tenant_payload


class FakeDynamoClient:
    def __init__(self, error_response: dict) -> None:
        self.error_response = error_response

    def transact_write_items(self, **kwargs) -> None:
        raise ClientError(self.error_response, "TransactWriteItems")


class FakeTable:
    table_name = "unit-tenants"

    def __init__(self, error_response: dict) -> None:
        self.meta = SimpleNamespace(client=FakeDynamoClient(error_response))


def _lead() -> EnterpriseLead:
    command = ConfirmOnboardingOtpCommand(
        verification_id="verification-1",
        otp="123456",
        **tenant_payload(),
    )
    return EnterpriseLead.create(command, plan_id="uuid-enterprise")


class EnterpriseLeadRepositoryTests(unittest.TestCase):
    def test_extra_conditional_transaction_failure_is_reported_separately(self) -> None:
        repo = DynamoEnterpriseLeadRepository(
            FakeTable(
                {
                    "Error": {"Code": "TransactionCanceledException", "Message": "cancelled"},
                    "CancellationReasons": [
                        {"Code": "None"},
                        {"Code": "ConditionalCheckFailed"},
                    ],
                }
            )
        )

        with self.assertRaises(ExtraTransactionConditionFailedError):
            repo.commit(
                lead=_lead(),
                events=[],
                idempotency=None,
                response=None,
                extra_transact_items=[{"Update": {"Key": {"id": "verification-1"}}}],
            )

    def test_lead_conditional_transaction_failure_maps_to_database_error(self) -> None:
        repo = DynamoEnterpriseLeadRepository(
            FakeTable(
                {
                    "Error": {"Code": "TransactionCanceledException", "Message": "cancelled"},
                    "CancellationReasons": [
                        {"Code": "ConditionalCheckFailed"},
                        {"Code": "None"},
                    ],
                }
            )
        )

        with self.assertRaises(DatabaseError):
            repo.commit(
                lead=_lead(),
                events=[],
                idempotency=None,
                response=None,
                extra_transact_items=[{"Update": {"Key": {"id": "verification-1"}}}],
            )

    def test_non_conditional_transaction_failure_maps_to_database_error(self) -> None:
        repo = DynamoEnterpriseLeadRepository(
            FakeTable(
                {
                    "Error": {"Code": "TransactionCanceledException", "Message": "cancelled"},
                    "CancellationReasons": [
                        {"Code": "None"},
                        {"Code": "ProvisionedThroughputExceeded"},
                    ],
                }
            )
        )

        with self.assertRaises(DatabaseError):
            repo.commit(
                lead=_lead(),
                events=[],
                idempotency=None,
                response=None,
                extra_transact_items=[{"Update": {"Key": {"id": "verification-1"}}}],
            )


if __name__ == "__main__":
    unittest.main()
