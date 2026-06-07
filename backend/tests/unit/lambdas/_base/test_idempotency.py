from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from lambdas._base import idempotency
from botocore.exceptions import ClientError
from shared.errors import IdempotencyKeyReusedError, ValidationError


def _request(**overrides):
    data = {
        "tenant_id": "tenant-1",
        "user_id": "user-1",
        "idempotency_key": "idem-1",
        "method": "POST",
        "path": "/tenants",
        "body_hash": "hash-1",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _make_client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "op")


class FakeIdempotencyTable:
    def __init__(self, item: dict | None = None) -> None:
        self.item = item
        self.put_calls = []
        self.update_calls = []

    def get_item(self, **kwargs):
        if self.item is None:
            return {}
        return {"Item": self.item}

    def put_item(self, **kwargs):
        self.put_calls.append(kwargs)
        self.item = kwargs["Item"]

    def update_item(self, **kwargs):
        self.update_calls.append(kwargs)


class RaceConditionTable(FakeIdempotencyTable):
    """Simulates the race window: _reserve() put_item fails because another
    request already completed the operation between our _existing() read and
    our put_item call."""

    def __init__(self, completed_item: dict) -> None:
        super().__init__(item=None)          # first get_item → None (no item yet)
        self._completed = completed_item
        self._get_count = 0

    def get_item(self, **kwargs):
        self._get_count += 1
        if self._get_count == 1:
            return {}                        # first call: item doesn't exist yet
        return {"Item": self._completed}     # second call (inside _reserve): COMPLETED

    def put_item(self, **kwargs):
        self.put_calls.append(kwargs)
        raise _make_client_error("ConditionalCheckFailedException")


class IdempotencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_table_name = idempotency._TABLE_NAME
        self.original_table = idempotency._table
        idempotency._TABLE_NAME = "unit-idempotency"

    def tearDown(self) -> None:
        idempotency._TABLE_NAME = self.original_table_name
        idempotency._table = self.original_table

    def test_requires_idempotency_key_when_table_is_enabled(self) -> None:
        idempotency._table = FakeIdempotencyTable()
        wrapped = idempotency.idempotent(lambda request, context: {"ok": True})

        with self.assertRaises(ValidationError):
            wrapped(_request(idempotency_key=None), object())

    def test_returns_cached_response_for_completed_matching_request(self) -> None:
        cached_response = {"statusCode": 201, "body": "{}"}
        table = FakeIdempotencyTable({
            "pk": "TENANT#tenant-1#idem-1",
            "method": "POST",
            "path": "/tenants",
            "body_hash": "hash-1",
            "status": "COMPLETED",
            "response": json.dumps(cached_response),
            "ttl": 99_999_999_999,
        })
        idempotency._table = table
        calls = []

        wrapped = idempotency.idempotent(lambda request, context: calls.append(True))
        response = wrapped(_request(), object())

        self.assertEqual(response, cached_response)
        self.assertEqual(calls, [])
        self.assertEqual(table.put_calls, [])

    def test_race_condition_reserve_returns_cached_response_when_completed_concurrently(self) -> None:
        cached_response = {"statusCode": 201, "body": '{"id":"t-1"}'}
        completed_item = {
            "pk":        "TENANT#tenant-1#idem-1",
            "method":    "POST",
            "path":      "/tenants",
            "body_hash": "hash-1",
            "status":    "COMPLETED",
            "response":  json.dumps(cached_response),
            "ttl":       99_999_999_999,
        }
        idempotency._table = RaceConditionTable(completed_item)
        handler_calls = []

        wrapped = idempotency.idempotent(lambda req, ctx: handler_calls.append(True))
        result = wrapped(_request(), object())

        self.assertEqual(result, cached_response)
        self.assertEqual(handler_calls, [], "handler must NOT run when race detects COMPLETED")

    def test_rejects_reused_key_with_different_body_hash(self) -> None:
        idempotency._table = FakeIdempotencyTable({
            "pk": "TENANT#tenant-1#idem-1",
            "method": "POST",
            "path": "/tenants",
            "body_hash": "hash-original",
            "status": "COMPLETED",
            "response": "{}",
            "ttl": 99_999_999_999,
        })
        wrapped = idempotency.idempotent(lambda request, context: {"ok": True})

        with self.assertRaises(IdempotencyKeyReusedError):
            wrapped(_request(body_hash="hash-new"), object())


if __name__ == "__main__":
    unittest.main()
