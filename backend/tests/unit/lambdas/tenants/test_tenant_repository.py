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


class ScanTable:
    table_name = "unit-tenants"

    def __init__(self, scan_responses: list[dict]) -> None:
        self.scan_responses = scan_responses
        self.scan_calls: list[dict] = []

    def scan(self, **kwargs) -> dict:
        self.scan_calls.append(kwargs)
        return self.scan_responses.pop(0)


class TenantRepositoryCountTests(unittest.TestCase):
    def test_sums_count_across_pages(self) -> None:
        table = ScanTable(
            scan_responses=[
                {"Count": 5, "LastEvaluatedKey": {"id": "tenant-x"}},
                {"Count": 2},
            ]
        )
        repo = DynamoTenantRepository(table)

        total = repo.count(status="active")

        self.assertEqual(total, 7)
        self.assertEqual(table.scan_calls[0]["Select"], "COUNT")


def _tenant_item(
    *,
    id: str,  # noqa: A002
    created_at: str = "2026-06-15T00:00:00+00:00",
    sri_environment: str = "testing",
    subscription_status: str | None = "active",
    plan_id: str = "uuid-basic",
) -> dict:
    return {
        "id": id,
        "ruc": "1790012345001",
        "email": "owner@example.com",
        "created_at": created_at,
        "updated_at": created_at,
        "entity_type": "TENANT",
        "deleted": False,
        "sri_environment": sri_environment,
        "subscription_status": subscription_status,
        "plan_id": plan_id,
    }


class TenantRepositoryAggregateDashboardStatsTests(unittest.TestCase):
    def test_tallies_environment_subscription_and_active_plan_counts(self) -> None:
        from datetime import UTC, datetime

        table = ScanTable(
            scan_responses=[
                {
                    "Items": [
                        _tenant_item(
                            id="t-1",
                            created_at="2026-06-15T00:00:00+00:00",
                            sri_environment="production",
                            subscription_status="active",
                            plan_id="uuid-basic",
                        ),
                        _tenant_item(
                            id="t-2",
                            created_at="2026-01-01T00:00:00+00:00",
                            sri_environment="testing",
                            subscription_status="expired",
                            plan_id="uuid-basic",
                        ),
                    ],
                    "LastEvaluatedKey": {"id": "t-2"},
                },
                {
                    "Items": [
                        _tenant_item(
                            id="t-3",
                            created_at="2026-06-10T00:00:00+00:00",
                            sri_environment="production",
                            subscription_status="active",
                            plan_id="uuid-pro",
                        ),
                        _tenant_item(
                            id="t-4",
                            created_at="2026-05-15T00:00:00+00:00",
                            sri_environment="testing",
                            subscription_status="payment_failed",
                            plan_id="uuid-basic",
                        ),
                    ]
                },
            ]
        )
        repo = DynamoTenantRepository(table)

        stats = repo.aggregate_dashboard_stats(datetime(2026, 6, 20, tzinfo=UTC))

        self.assertEqual(stats.total, 4)
        self.assertEqual(stats.new_this_month, 2)  # t-1 and t-3, not t-2 (January)
        self.assertEqual(stats.new_previous_month, 1)  # t-4 (May)
        self.assertEqual(stats.by_environment, {"production": 2, "testing": 2})
        self.assertEqual(
            stats.by_subscription_status, {"active": 2, "expired": 1, "payment_failed": 1}
        )
        self.assertEqual(stats.active_by_plan_id, {"uuid-basic": 1, "uuid-pro": 1})
        self.assertEqual(len(table.scan_calls), 2)
        # Top 5 mas recientes, orden descendente por created_at
        self.assertEqual([t.id for t in stats.recent_tenants], ["t-1", "t-3", "t-4", "t-2"])


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
