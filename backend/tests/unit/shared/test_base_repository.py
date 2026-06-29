from __future__ import annotations

import unittest

from botocore.exceptions import ClientError

from shared.db.base_repository import BaseRepository
from shared.domain.base_entity import TenantScopedEntity
from shared.errors import DatabaseError, OptimisticLockError


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "TransactWriteItems")


def _transaction_cancelled_error() -> ClientError:
    return ClientError(
        {
            "Error": {"Code": "TransactionCanceledException"},
            "CancellationReasons": [{"Code": "ConditionalCheckFailed"}],
        },
        "TransactWriteItems",
    )


class FakeDynamoClient:
    def __init__(self) -> None:
        self.transact_items: list[list[dict]] = []
        self.error: ClientError | None = None

    def transact_write_items(self, **kwargs) -> None:
        if self.error is not None:
            raise self.error
        self.transact_items.append(kwargs["TransactItems"])


class FakeTableMeta:
    def __init__(self, client: FakeDynamoClient) -> None:
        self.client = client


class FakeTable:
    table_name = "unit-table"

    def __init__(self) -> None:
        self.client = FakeDynamoClient()
        self.meta = FakeTableMeta(self.client)
        self.items: dict[tuple[str, str], dict] = {}

    def get_item(self, **kwargs) -> dict:
        key = kwargs["Key"]
        item = self.items.get((key["pk"], key["sk"]))
        return {"Item": item} if item else {}


class FakeRepository(BaseRepository):
    _prefix = "FAKE"

    def _to_item(self, entity: TenantScopedEntity) -> dict:
        return {}

    def _from_item(self, item: dict) -> TenantScopedEntity:
        raise NotImplementedError


class BaseRepositoryTests(unittest.TestCase):
    def test_get_raw_excludes_soft_deleted_by_default(self) -> None:
        table = FakeTable()
        table.items[("TENANT#tenant-1", "FAKE#entity-1")] = {"id": "entity-1", "deleted": True}
        repo = FakeRepository("tenant-1", table)

        self.assertIsNone(repo._get_raw("entity-1"))

    def test_get_raw_can_include_soft_deleted_items(self) -> None:
        table = FakeTable()
        table.items[("TENANT#tenant-1", "FAKE#entity-1")] = {"id": "entity-1", "deleted": True}
        repo = FakeRepository("tenant-1", table)

        self.assertEqual(
            repo._get_raw("entity-1", include_deleted=True), {"id": "entity-1", "deleted": True}
        )

    def test_transact_write_items_executes_transact_write(self) -> None:
        table = FakeTable()
        repo = FakeRepository("tenant-1", table)
        transact_items = [{"Put": {"TableName": "unit-table", "Item": {"id": "1"}}}]

        repo._transact_write_items(transact_items)

        self.assertEqual(table.client.transact_items, [transact_items])

    def test_transact_write_items_maps_cancelled_transaction_to_optimistic_lock(self) -> None:
        table = FakeTable()
        table.client.error = _transaction_cancelled_error()
        repo = FakeRepository("tenant-1", table)

        with self.assertRaises(OptimisticLockError):
            repo._transact_write_items([])

    def test_transact_write_items_delegates_condition_error_mapping(self) -> None:
        table = FakeTable()
        table.client.error = _transaction_cancelled_error()
        repo = FakeRepository("tenant-1", table)

        def raise_custom_error(exc: ClientError, reasons: list[dict]) -> None:
            self.assertEqual(reasons[0]["code"], "ConditionalCheckFailed")
            raise ValueError("custom") from exc

        with self.assertRaisesRegex(ValueError, "custom"):
            repo._transact_write_items([], on_condition_error=raise_custom_error)

    def test_transact_write_items_maps_non_condition_error_to_database_error(self) -> None:
        table = FakeTable()
        table.client.error = _client_error("ProvisionedThroughputExceededException")
        repo = FakeRepository("tenant-1", table)

        with self.assertRaises(DatabaseError):
            repo._transact_write_items([])


if __name__ == "__main__":
    unittest.main()
