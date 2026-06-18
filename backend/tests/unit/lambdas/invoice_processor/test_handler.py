from __future__ import annotations

import importlib
import json
import os
import sys
import unittest

from tests.unit.support import LambdaContext, configure_unit_environment


def _load_handler():
    configure_unit_environment()
    os.environ["DOCUMENTS_TABLE"] = "unit-documents"
    os.environ["TENANTS_TABLE"] = "unit-tenants"
    os.environ["DOCUMENTS_BUCKET"] = "unit-bucket"
    os.environ["POLL_QUEUE_URL"] = ""
    os.environ["EMAIL_NOTIFICATIONS_QUEUE_URL"] = ""
    for mod in list(sys.modules):
        if mod.startswith("lambdas.invoice_processor.handler"):
            sys.modules.pop(mod, None)
    return importlib.import_module("lambdas.invoice_processor.handler")


def _sqs_event(body: dict, message_id: str = "msg-1") -> dict:
    return {
        "Records": [
            {
                "messageId": message_id,
                "receiptHandle": "receipt-1",
                "attributes": {},
                "body": json.dumps(body),
            }
        ]
    }


class FakeSignUseCase:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)


class FakePollUseCase:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)


class InvoiceProcessorHandlerTests(unittest.TestCase):
    def test_routes_sign_message_to_sign_use_case(self) -> None:
        mod = _load_handler()
        fake = FakeSignUseCase()
        mod._sign_use_case = fake

        result = mod.handler(
            _sqs_event({"type": "SIGN", "tenant_id": "t1", "document_id": "d1"}),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(fake.calls, [{"tenant_id": "t1", "document_id": "d1"}])

    def test_routes_poll_message_to_poll_use_case(self) -> None:
        mod = _load_handler()
        fake = FakePollUseCase()
        mod._poll_use_case = fake

        result = mod.handler(
            _sqs_event(
                {
                    "type": "POLL",
                    "tenant_id": "t1",
                    "document_id": "d1",
                    "access_key": "1" * 49,
                    "attempt": 2,
                }
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(
            fake.calls,
            [{"tenant_id": "t1", "document_id": "d1", "access_key": "1" * 49, "attempt": 2}],
        )

    def test_poll_message_defaults_attempt_to_1(self) -> None:
        mod = _load_handler()
        fake = FakePollUseCase()
        mod._poll_use_case = fake

        mod.handler(
            _sqs_event({"type": "POLL", "tenant_id": "t1", "document_id": "d1", "access_key": "k"}),
            LambdaContext(),
        )

        self.assertEqual(fake.calls[0]["attempt"], 1)

    def test_unknown_type_is_ignored_without_failure(self) -> None:
        mod = _load_handler()
        result = mod.handler(_sqs_event({"type": "WHATEVER"}), LambdaContext())
        self.assertEqual(result, {"batchItemFailures": []})

    def test_use_case_exception_marks_batch_item_failure(self) -> None:
        mod = _load_handler()

        class FailingUseCase:
            def execute(self, **kwargs):
                raise RuntimeError("boom")

        mod._sign_use_case = FailingUseCase()

        result = mod.handler(
            _sqs_event({"type": "SIGN", "tenant_id": "t1", "document_id": "d1"}),
            LambdaContext(),
        )

        self.assertEqual(result["batchItemFailures"], [{"itemIdentifier": "msg-1"}])


if __name__ == "__main__":
    unittest.main()
