from __future__ import annotations

import unittest
from types import SimpleNamespace

from botocore.exceptions import ClientError

from lambdas.tenants.domain.errors import TenantRucAlreadyExistsError
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from shared.db.transactions import ExtraTransactionConditionFailedError
from shared.errors import OptimisticLockError
from tests.unit.support import make_tenant


class FakeDynamoClient:
    def __init__(self, error_response: dict) -> None:
        self.error_response = error_response

    def transact_write_items(self, **kwargs) -> None:
        raise ClientError(self.error_response, "TransactWriteItems")


class FakeTable:
    table_name = "unit-tenants"

    def __init__(self, error_response: dict) -> None:
        self.meta = SimpleNamespace(client=FakeDynamoClient(error_response))

    def get_item(self, **kwargs) -> dict:
        return {}


class CapturingDynamoClient:
    def __init__(self, error_response: dict | None = None) -> None:
        self.error_response = error_response
        self.transact_write_calls: list[dict] = []

    def transact_write_items(self, **kwargs) -> None:
        self.transact_write_calls.append(kwargs)
        if self.error_response:
            raise ClientError(self.error_response, "TransactWriteItems")


class ExistingTenantTable:
    table_name = "unit-tenants"

    def __init__(self, item: dict, error_response: dict | None = None) -> None:
        self.item = item
        self.client = CapturingDynamoClient(error_response)
        self.meta = SimpleNamespace(client=self.client)

    def get_item(self, **kwargs) -> dict:
        return {"Item": self.item}


def _transaction_cancelled(reasons: list[dict]) -> dict:
    return {
        "Error": {"Code": "TransactionCanceledException", "Message": "cancelled"},
        "CancellationReasons": reasons,
    }


class TenantRepositoryTests(unittest.TestCase):
    def test_create_ruc_condition_failure_keeps_tenant_conflict_mapping(self) -> None:
        repo = DynamoTenantRepository(
            FakeTable(
                _transaction_cancelled(
                    [
                        {"Code": "ConditionalCheckFailed"},
                        {"Code": "None"},
                        {"Code": "None"},
                    ]
                )
            )
        )

        with self.assertRaises(TenantRucAlreadyExistsError):
            repo.commit(
                tenant=make_tenant(),
                user_id="onboarding",
                action="CREATE",
                events=[],
                idempotency=None,
                response=None,
                extra_transact_items=[{"Update": {"Key": {"id": "verification-1"}}}],
            )

    def test_extra_condition_failure_is_reported_separately(self) -> None:
        repo = DynamoTenantRepository(
            FakeTable(
                _transaction_cancelled(
                    [
                        {"Code": "None"},
                        {"Code": "None"},
                        {"Code": "ConditionalCheckFailed"},
                    ]
                )
            )
        )

        with self.assertRaises(ExtraTransactionConditionFailedError):
            repo.commit(
                tenant=make_tenant(),
                user_id="onboarding",
                action="CREATE",
                events=[],
                idempotency=None,
                response=None,
                extra_transact_items=[{"Update": {"Key": {"id": "verification-1"}}}],
            )

    def test_commit_admin_events_condition_checks_current_tenant_version(self) -> None:
        tenant = make_tenant(id="tenant-retry-1", version=4)
        table = ExistingTenantTable({"id": tenant.id, "version": tenant.version, "deleted": False})
        repo = DynamoTenantRepository(table)

        repo.commit_admin_events(
            tenant=tenant,
            user_id="admin-1",
            action="ONBOARDING_RETRY",
            events=[],
            idempotency=None,
            response=None,
        )

        transact_items = table.client.transact_write_calls[0]["TransactItems"]
        self.assertEqual(len(transact_items), 1)
        condition = transact_items[0]["ConditionCheck"]
        self.assertEqual(condition["TableName"], "unit-tenants")
        self.assertEqual(condition["Key"], {"id": "tenant-retry-1"})
        self.assertEqual(condition["ExpressionAttributeValues"][":version"], 4)
        self.assertEqual(condition["ExpressionAttributeValues"][":deleted"], False)

    def test_commit_admin_events_stale_tenant_raises_optimistic_lock(self) -> None:
        tenant = make_tenant(id="tenant-retry-1", version=4)
        repo = DynamoTenantRepository(
            ExistingTenantTable(
                {"id": tenant.id, "version": tenant.version, "deleted": False},
                _transaction_cancelled([{"Code": "ConditionalCheckFailed"}]),
            )
        )

        with self.assertRaises(OptimisticLockError):
            repo.commit_admin_events(
                tenant=tenant,
                user_id="admin-1",
                action="ONBOARDING_RETRY",
                events=[],
                idempotency=None,
                response=None,
            )


if __name__ == "__main__":
    unittest.main()
