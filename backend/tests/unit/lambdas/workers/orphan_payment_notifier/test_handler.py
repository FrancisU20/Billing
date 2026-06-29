from __future__ import annotations

import importlib
import os
import sys
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from botocore.exceptions import ClientError

from tests.unit.support import configure_unit_environment

configure_unit_environment()
os.environ.setdefault("PAYMENTS_TABLE", "unit-payments")
os.environ.setdefault("SUPERADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("BREVO_SECRET_NAME", "unit/brevo")
os.environ.setdefault("BREVO_SENDER_EMAIL", "no-reply@example.com")
os.environ.setdefault("BREVO_BILLING_EMAIL", "billing@example.com")


def _reload_handler():
    mod_name = "lambdas.workers.orphan_payment_notifier.handler"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    with patch("shared.db.client.get_table"):
        return importlib.import_module(mod_name)


_handler_mod = _reload_handler()


def _conditional_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "condition failed"}},
        "UpdateItem",
    )


def _condition_contains_name(expression, name: str) -> bool:
    node = expression.get_expression()
    for value in node.get("values", ()):
        if getattr(value, "name", None) == name:
            return True
        if hasattr(value, "get_expression") and _condition_contains_name(value, name):
            return True
    return False


class FakePaymentsTable:
    def __init__(self) -> None:
        self.scan_calls: list[dict] = []
        self.updated: list[dict] = []
        self.conditional_fail = False

    def scan(self, **kwargs) -> dict:
        self.scan_calls.append(kwargs)
        return {"Items": []}

    def update_item(self, **kwargs) -> dict:
        self.updated.append(kwargs)
        if self.conditional_fail:
            raise _conditional_error()
        return {}


class DynamoOrphanPaymentQueryTests(unittest.TestCase):
    def test_scan_excludes_already_alerted_orphans(self) -> None:
        table = FakePaymentsTable()
        query = _handler_mod._DynamoOrphanPaymentQuery(table)

        query.list_orphaned_paid(cutoff=datetime(2026, 6, 28, 10, 0, tzinfo=UTC))

        expression = table.scan_calls[0]["FilterExpression"]
        self.assertTrue(_condition_contains_name(expression, "orphan_alerted_at"))

    def test_mark_orphan_alert_sent_updates_with_condition(self) -> None:
        table = FakePaymentsTable()
        query = _handler_mod._DynamoOrphanPaymentQuery(table)

        updated = query.mark_orphan_alert_sent(
            order_id="DP-1",
            alerted_at=datetime(2026, 6, 28, 10, 0, tzinfo=UTC),
        )

        self.assertTrue(updated)
        call = table.updated[0]
        self.assertIn("orphan_alerted_at", call["UpdateExpression"])
        self.assertIn("attribute_not_exists(orphan_alerted_at)", call["ConditionExpression"])

    def test_mark_orphan_alert_sent_returns_false_on_conditional_failure(self) -> None:
        table = FakePaymentsTable()
        table.conditional_fail = True
        query = _handler_mod._DynamoOrphanPaymentQuery(table)

        updated = query.mark_orphan_alert_sent(
            order_id="DP-1",
            alerted_at=datetime(2026, 6, 28, 10, 0, tzinfo=UTC),
        )

        self.assertFalse(updated)


if __name__ == "__main__":
    unittest.main()
