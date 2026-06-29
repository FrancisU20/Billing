from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from unittest.mock import patch

from tests.unit.support import LambdaContext, configure_unit_environment

configure_unit_environment()
os.environ.setdefault("PAYMENTS_TABLE", "unit-payments")
os.environ.setdefault("DLOCAL_WEBHOOK_QUEUE_NAME", "unit-dlocal-webhooks")


def _reload_handler():
    mod_name = "lambdas.workers.dlocal_webhook_processor.handler"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    with patch("shared.db.client.get_table"):
        return importlib.import_module(mod_name)


_handler_mod = _reload_handler()


class FakePaymentRepository:
    def __init__(self, *, raises: Exception | None = None) -> None:
        self.raises = raises
        self.applied: list[tuple[str, str]] = []

    def apply_webhook_status(self, order_id: str, new_status: str) -> tuple[str, bool]:
        self.applied.append((order_id, new_status))
        if self.raises:
            raise self.raises
        return new_status, True


def _sqs_event(body: dict, *, message_id: str = "msg-1") -> dict:
    return {
        "Records": [
            {
                "messageId": message_id,
                "receiptHandle": f"rh-{message_id}",
                "attributes": {},
                "body": json.dumps(body),
            }
        ]
    }


def _webhook_message(payload: dict) -> dict:
    return {
        "type": "DLOCAL_WEBHOOK",
        "raw_body": json.dumps(payload),
        "request_id": "req-1",
    }


class DLocalWebhookProcessorHandlerTests(unittest.TestCase):
    def test_processes_payment_webhook(self) -> None:
        repo = FakePaymentRepository()
        _handler_mod._use_case = _handler_mod.ProcessWebhookUseCase(repo)

        response = _handler_mod.handler(
            _sqs_event(
                _webhook_message(
                    {"type": "PAYMENT", "data": {"order_id": "DP-1", "status": "PAID"}}
                )
            ),
            LambdaContext(),
        )

        self.assertEqual(response, {"batchItemFailures": []})
        self.assertEqual(repo.applied, [("DP-1", "PAID")])

    def test_ignores_non_payment_webhook(self) -> None:
        repo = FakePaymentRepository()
        _handler_mod._use_case = _handler_mod.ProcessWebhookUseCase(repo)

        response = _handler_mod.handler(
            _sqs_event(_webhook_message({"type": "REFUND", "data": {"order_id": "DP-1"}})),
            LambdaContext(),
        )

        self.assertEqual(response, {"batchItemFailures": []})
        self.assertEqual(repo.applied, [])

    def test_failed_processing_marks_only_record_as_failed_for_retry_and_dlq(self) -> None:
        repo = FakePaymentRepository(raises=RuntimeError("dynamo unavailable"))
        _handler_mod._use_case = _handler_mod.ProcessWebhookUseCase(repo)

        response = _handler_mod.handler(
            _sqs_event(
                _webhook_message(
                    {"type": "PAYMENT", "data": {"order_id": "DP-1", "status": "PAID"}}
                )
            ),
            LambdaContext(),
        )

        self.assertEqual(response, {"batchItemFailures": [{"itemIdentifier": "msg-1"}]})
        self.assertEqual(repo.applied, [("DP-1", "PAID")])

    def test_invalid_raw_payload_marks_record_as_failed(self) -> None:
        response = _handler_mod.handler(
            _sqs_event({"type": "DLOCAL_WEBHOOK", "raw_body": "not-json"}),
            LambdaContext(),
        )

        self.assertEqual(response, {"batchItemFailures": [{"itemIdentifier": "msg-1"}]})


if __name__ == "__main__":
    unittest.main()
