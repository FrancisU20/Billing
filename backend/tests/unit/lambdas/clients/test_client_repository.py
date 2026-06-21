from __future__ import annotations

import unittest

from botocore.exceptions import ClientError

from lambdas.clients.domain.commands import UpdateClientCommand
from lambdas.clients.domain.errors import ClientDuplicateIdentificationError
from lambdas.clients.infra.client_repository import DynamoClientRepository
from shared.errors import OptimisticLockError
from tests.unit.support import make_client


class FakeDynamoClient:
    def __init__(self, error_response: dict | None = None) -> None:
        self.transact_items: list[dict] | None = None
        self.error_response = error_response

    def transact_write_items(self, **kwargs) -> None:
        self.transact_items = kwargs["TransactItems"]
        if self.error_response:
            raise ClientError(self.error_response, "TransactWriteItems")


class FakeMeta:
    def __init__(self, client: FakeDynamoClient) -> None:
        self.client = client


class FakeClientsTable:
    table_name = "unit-clients"

    def __init__(
        self,
        old_item: dict | None = None,
        error_response: dict | None = None,
        query_items: list[dict] | None = None,
        query_responses: list[dict] | None = None,
    ) -> None:
        self.old_item = old_item
        self.query_items = query_items or []
        self.query_responses = query_responses or []
        self.query_calls: list[dict] = []
        self.client = FakeDynamoClient(error_response)
        self.meta = FakeMeta(self.client)

    def get_item(self, **kwargs) -> dict:
        return {"Item": self.old_item} if self.old_item else {}

    def query(self, **kwargs) -> dict:
        self.query_calls.append(kwargs)
        if self.query_responses:
            return self.query_responses.pop(0)
        return {"Items": self.query_items}


class DynamoClientRepositoryTests(unittest.TestCase):
    def test_create_writes_identification_lock_and_client_item(self) -> None:
        table = FakeClientsTable()
        repo = DynamoClientRepository("tenant-1", table)
        client = make_client(id="client-1", tenant_id="tenant-1")

        repo.commit(
            client=client,
            user_id="admin-1",
            action="CREATE",
            idempotency=None,
            response=None,
        )

        items = table.client.transact_items
        self.assertIsNotNone(items)
        self.assertEqual(items[0]["Put"]["Item"]["sk"], "CLIENT_IDENTIFICATION#1792146739001")
        self.assertEqual(items[1]["Put"]["Item"]["sk"], "CLIENT#client-1")

    def test_delete_removes_identification_lock_in_same_transaction(self) -> None:
        client = make_client(id="client-1", tenant_id="tenant-1")
        table = FakeClientsTable(
            DynamoClientRepository("tenant-1", FakeClientsTable())._to_item(client)
        )
        repo = DynamoClientRepository("tenant-1", table)
        client.soft_delete("admin-1")

        repo.commit(
            client=client,
            user_id="admin-1",
            action="DELETE",
            idempotency=None,
            response=None,
        )

        items = table.client.transact_items
        self.assertIsNotNone(items)
        self.assertEqual(items[0]["Delete"]["Key"]["sk"], "CLIENT_IDENTIFICATION#1792146739001")
        self.assertEqual(items[1]["Put"]["Item"]["deleted"], True)

    def test_list_by_identification_uses_identification_index(self) -> None:
        client = make_client(id="client-1", tenant_id="tenant-1")
        table = FakeClientsTable(
            query_items=[DynamoClientRepository("tenant-1", FakeClientsTable())._to_item(client)]
        )
        repo = DynamoClientRepository("tenant-1", table)

        clients, next_token = repo.list(
            limit=20,
            next_token=None,
            identification="1792146739001",
        )

        self.assertEqual([c.id for c in clients], ["client-1"])
        self.assertIsNone(next_token)
        self.assertEqual(table.query_calls[0]["IndexName"], "identification-index")

    def test_list_by_identification_prefix_finds_partial_match(self) -> None:
        """Typing "1003" should find "1003368725" via begins_with on the GSI sort
        key — no table-wide walk needed."""
        client = make_client(id="client-1", tenant_id="tenant-1", identification="1003368725")
        table = FakeClientsTable(
            query_items=[DynamoClientRepository("tenant-1", FakeClientsTable())._to_item(client)]
        )
        repo = DynamoClientRepository("tenant-1", table)

        clients, _ = repo.list(limit=20, next_token=None, identification="1003")

        self.assertEqual([c.id for c in clients], ["client-1"])
        self.assertEqual(table.query_calls[0]["IndexName"], "identification-index")
        condition = table.query_calls[0]["KeyConditionExpression"]
        begins_with_condition = condition.get_expression()["values"][1]
        self.assertEqual(begins_with_condition.get_expression()["operator"], "begins_with")
        self.assertEqual(begins_with_condition.get_expression()["values"][1], "1003")

    def test_count_sums_across_pages(self) -> None:
        table = FakeClientsTable(
            query_responses=[
                {"Count": 7, "LastEvaluatedKey": {"pk": "TENANT#tenant-1", "sk": "CLIENT#x"}},
                {"Count": 3},
            ]
        )
        repo = DynamoClientRepository("tenant-1", table)

        total = repo.count(status="active")

        self.assertEqual(total, 10)
        self.assertEqual(table.query_calls[0]["Select"], "COUNT")

    def test_count_by_identification_prefix_uses_select_count_on_gsi(self) -> None:
        table = FakeClientsTable(
            query_responses=[
                {"Count": 2, "LastEvaluatedKey": {"pk": "TENANT#tenant-1", "sk": "CLIENT#x"}},
                {"Count": 1},
            ]
        )
        repo = DynamoClientRepository("tenant-1", table)

        total = repo.count(identification="1003")

        self.assertEqual(total, 3)
        self.assertEqual(table.query_calls[0]["IndexName"], "identification-index")
        self.assertEqual(table.query_calls[0]["Select"], "COUNT")

    def test_q_search_walks_pages_until_it_finds_matches(self) -> None:
        non_match = make_client(id="client-1", tenant_id="tenant-1", legal_name="Otro Cliente")
        match = make_client(id="client-2", tenant_id="tenant-1", legal_name="Acme Ecuador")
        mapper = DynamoClientRepository("tenant-1", FakeClientsTable())
        table = FakeClientsTable(
            query_responses=[
                {
                    "Items": [mapper._to_item(non_match)],
                    "LastEvaluatedKey": {"pk": "TENANT#tenant-1", "sk": "CLIENT#client-1"},
                },
                {"Items": [mapper._to_item(match)]},
            ]
        )
        repo = DynamoClientRepository("tenant-1", table)

        clients, next_token = repo.list(limit=1, next_token=None, q="acme")

        self.assertEqual([c.id for c in clients], ["client-2"])
        self.assertIsNone(next_token)
        self.assertEqual(len(table.query_calls), 2)
        self.assertIn("ExclusiveStartKey", table.query_calls[1])

    def test_update_version_failure_maps_to_optimistic_lock(self) -> None:
        client = make_client(id="client-1", tenant_id="tenant-1")
        old_item = DynamoClientRepository("tenant-1", FakeClientsTable())._to_item(client)
        client.update(
            UpdateClientCommand(client_id="client-1", updated_by="admin-1", trade_name="Nuevo")
        )
        table = FakeClientsTable(
            old_item,
            _transaction_cancelled([{"Code": "ConditionalCheckFailed", "Message": ""}]),
        )
        repo = DynamoClientRepository("tenant-1", table)

        with self.assertRaises(OptimisticLockError):
            repo.commit(
                client=client,
                user_id="admin-1",
                action="UPDATE",
                idempotency=None,
                response=None,
            )

    def test_create_lock_failure_maps_to_duplicate_identification(self) -> None:
        table = FakeClientsTable(
            None,
            _transaction_cancelled(
                [
                    {"Code": "ConditionalCheckFailed", "Message": ""},
                    {"Code": "None", "Message": ""},
                ]
            ),
        )
        repo = DynamoClientRepository("tenant-1", table)
        client = make_client(id="client-1", tenant_id="tenant-1")

        with self.assertRaises(ClientDuplicateIdentificationError):
            repo.commit(
                client=client,
                user_id="admin-1",
                action="CREATE",
                idempotency=None,
                response=None,
            )


def _transaction_cancelled(reasons: list[dict]) -> dict:
    return {
        "Error": {"Code": "TransactionCanceledException", "Message": "cancelled"},
        "CancellationReasons": reasons,
    }


if __name__ == "__main__":
    unittest.main()
