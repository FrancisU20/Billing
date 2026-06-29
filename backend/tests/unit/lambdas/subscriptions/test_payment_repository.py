from __future__ import annotations

import unittest
from datetime import datetime

from botocore.exceptions import ClientError

from lambdas.subscriptions.infra.payment_repository import DynamoPaymentRepository


def _conditional_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "condition failed"}},
        "UpdateItem",
    )


class FakePaymentsTable:
    table_name = "payments"

    def __init__(self, item: dict | None = None) -> None:
        self.item = item
        self.update_calls: list[dict] = []

    def update_item(self, **kwargs) -> dict:
        self.update_calls.append(kwargs)
        if not self.item:
            raise _conditional_error()

        current_status = self.item["status"]
        values = kwargs["ExpressionAttributeValues"]
        new_status = values.get(":new_status") or values.get(":cancelled")
        condition = kwargs["ConditionExpression"]

        if "#status IN (:created, :pending)" in condition and current_status not in {
            "CREATED",
            "PENDING",
        }:
            raise _conditional_error()
        if "#status <> :paid AND #status <> :refunded" in condition and current_status in {
            "PAID",
            "REFUNDED",
        }:
            raise _conditional_error()
        if "created_at <= :cutoff" in condition and self.item["created_at"] > values[":cutoff"]:
            raise _conditional_error()

        self.item["status"] = new_status
        if ":detail" in values:
            self.item["error_detail"] = values[":detail"]
        if new_status == "PAID" and "confirmed_at" not in self.item:
            self.item["confirmed_at"] = values[":now"]
        return {"Attributes": self.item}

    def get_item(self, **kwargs) -> dict:
        if not self.item:
            return {}
        return {"Item": self.item}


class DynamoPaymentRepositoryWebhookStatusTests(unittest.TestCase):
    def _item(self, *, status: str = "PENDING") -> dict:
        return {
            "id": "PAYMENT#DP-1",
            "order_id": "DP-1",
            "tenant_id": "tenant-1",
            "plan_id": "plan-1",
            "amount": "10.00",
            "currency": "USD",
            "status": status,
            "plan_cycle": "month",
            "created_at": "2026-06-28T10:00:00+00:00",
        }

    def test_apply_webhook_paid_uses_conditional_update_and_sets_confirmed_at(self) -> None:
        table = FakePaymentsTable(self._item(status="PENDING"))
        status, updated = DynamoPaymentRepository(table).apply_webhook_status("DP-1", "PAID")

        self.assertTrue(updated)
        self.assertEqual(status, "PAID")
        self.assertEqual(table.item["status"], "PAID")
        self.assertIn("confirmed_at", table.item)
        self.assertIn(
            "#status <> :paid AND #status <> :refunded",
            table.update_calls[0]["ConditionExpression"],
        )

    def test_negative_webhook_cannot_downgrade_paid_payment(self) -> None:
        table = FakePaymentsTable(self._item(status="PAID"))
        status, updated = DynamoPaymentRepository(table).apply_webhook_status("DP-1", "FAILED")

        self.assertFalse(updated)
        self.assertEqual(status, "PAID")
        self.assertEqual(table.item["status"], "PAID")

    def test_negative_webhook_can_close_pending_payment(self) -> None:
        table = FakePaymentsTable(self._item(status="PENDING"))
        status, updated = DynamoPaymentRepository(table).apply_webhook_status("DP-1", "REJECTED")

        self.assertTrue(updated)
        self.assertEqual(status, "REJECTED")
        self.assertEqual(table.item["status"], "REJECTED")
        self.assertIn(
            "#status IN (:created, :pending)", table.update_calls[0]["ConditionExpression"]
        )

    def test_paid_webhook_does_not_change_refunded_payment(self) -> None:
        table = FakePaymentsTable(self._item(status="REFUNDED"))
        status, updated = DynamoPaymentRepository(table).apply_webhook_status("DP-1", "PAID")

        self.assertFalse(updated)
        self.assertEqual(status, "REFUNDED")
        self.assertEqual(table.item["status"], "REFUNDED")

    def test_cancel_stale_open_payment_uses_conditional_update(self) -> None:
        table = FakePaymentsTable(self._item(status="PENDING"))

        updated = DynamoPaymentRepository(table).cancel_stale_open_payment(
            order_id="DP-1",
            cutoff=datetime.fromisoformat("2026-06-28T11:00:00+00:00"),
        )

        self.assertTrue(updated)
        self.assertEqual(table.item["status"], "CANCELLED")
        self.assertEqual(table.item["error_detail"], "Expired by stale payment cleaner")
        self.assertIn("created_at <= :cutoff", table.update_calls[0]["ConditionExpression"])

    def test_cancel_stale_open_payment_does_not_overwrite_paid_payment(self) -> None:
        table = FakePaymentsTable(self._item(status="PAID"))

        updated = DynamoPaymentRepository(table).cancel_stale_open_payment(
            order_id="DP-1",
            cutoff=datetime.fromisoformat("2026-06-28T11:00:00+00:00"),
        )

        self.assertFalse(updated)
        self.assertEqual(table.item["status"], "PAID")


if __name__ == "__main__":
    unittest.main()
