from __future__ import annotations

import unittest

from botocore.exceptions import ClientError

from shared.db.transactions import (
    cancellation_reasons,
    conditional_failure_indexes,
    failed_put_item_entity_type,
    has_conditional_failure_at,
    is_transaction_condition_error,
)


def _client_error(code: str, *, reasons: list[dict] | None = None) -> ClientError:
    response = {"Error": {"Code": code, "Message": "error"}}
    if reasons is not None:
        response["CancellationReasons"] = reasons
    return ClientError(response, "TransactWriteItems")


class DynamoTransactionHelpersTests(unittest.TestCase):
    def test_normalizes_cancellation_reasons(self) -> None:
        exc = _client_error(
            "TransactionCanceledException",
            reasons=[
                {"Code": "ConditionalCheckFailed", "Message": "lock exists"},
                {},
            ],
        )

        self.assertEqual(
            cancellation_reasons(exc),
            [
                {"code": "ConditionalCheckFailed", "msg": "lock exists"},
                {"code": "None", "msg": ""},
            ],
        )

    def test_detects_transaction_condition_error_codes(self) -> None:
        self.assertTrue(
            is_transaction_condition_error(_client_error("TransactionCanceledException"))
        )
        self.assertTrue(
            is_transaction_condition_error(_client_error("ConditionalCheckFailedException"))
        )
        self.assertFalse(is_transaction_condition_error(_client_error("InternalServerError")))

    def test_returns_conditional_failure_indexes_from_cancellation_reasons(self) -> None:
        exc = _client_error(
            "TransactionCanceledException",
            reasons=[
                {"Code": "None"},
                {"Code": "ConditionalCheckFailed"},
                {"Code": "ConditionalCheckFailed"},
            ],
        )

        self.assertEqual(conditional_failure_indexes(exc), {1, 2})
        self.assertTrue(has_conditional_failure_at(exc, {0, 2}))
        self.assertFalse(has_conditional_failure_at(exc, {0}))

    def test_single_update_conditional_failure_maps_to_first_item(self) -> None:
        exc = _client_error("ConditionalCheckFailedException")

        self.assertEqual(conditional_failure_indexes(exc), {0})

    def test_non_condition_error_has_no_conditional_failures(self) -> None:
        exc = _client_error("InternalServerError")

        self.assertEqual(conditional_failure_indexes(exc), set())

    def test_detects_failed_put_item_by_entity_type(self) -> None:
        exc = _client_error(
            "TransactionCanceledException",
            reasons=[
                {"Code": "None"},
                {"Code": "ConditionalCheckFailed"},
            ],
        )
        transact_items = [
            {"Put": {"Item": {"entity_type": "CLIENT"}}},
            {"Put": {"Item": {"entity_type": "CLIENT_IDENTIFICATION_LOCK"}}},
        ]

        self.assertTrue(
            failed_put_item_entity_type(transact_items, exc, "CLIENT_IDENTIFICATION_LOCK")
        )
        self.assertFalse(failed_put_item_entity_type(transact_items, exc, "PRODUCT_SKU_LOCK"))

    def test_failed_put_item_uses_default_when_dynamodb_does_not_return_indexes(self) -> None:
        exc = _client_error("TransactionCanceledException")

        self.assertTrue(
            failed_put_item_entity_type(
                [],
                exc,
                "CLIENT_IDENTIFICATION_LOCK",
                default_when_unindexed=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
