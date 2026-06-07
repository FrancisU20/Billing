from __future__ import annotations

import importlib
import os
import sys
import unittest

from boto3.dynamodb.types import TypeSerializer

from tests.unit.support import LambdaContext, configure_unit_environment

_serializer = TypeSerializer()


def _load_outbox_relay_module():
    configure_unit_environment()
    os.environ["OUTBOX_TABLE"] = "unit-outbox"
    os.environ["EVENTS_QUEUE_URL"] = "https://sqs.example/tenant-onboarding"
    sys.modules.pop("lambdas.workers.outbox_relay.handler", None)
    return importlib.import_module("lambdas.workers.outbox_relay.handler")


def _stream_event(item: dict, sequence_number: str = "seq-1") -> dict:
    return {
        "Records": [
            {
                "eventID": "event-1",
                "eventName": "INSERT",
                "dynamodb": {
                    "SequenceNumber": sequence_number,
                    "NewImage": {key: _serializer.serialize(value) for key, value in item.items()},
                },
            }
        ]
    }


def _pending_item(event_type: str = "TenantCreatedEvent") -> dict:
    return {
        "id": "event-id-1",
        "status": "PENDING",
        "event_type": event_type,
        "payload": '{"event_type":"TenantCreatedEvent"}',
    }


class FakeSqs:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.sent_messages = []

    def send_message(self, **kwargs):
        if self.fail:
            raise RuntimeError("SQS unavailable")
        self.sent_messages.append(kwargs)


class FakeOutboxTable:
    def __init__(self) -> None:
        self.update_calls = []

    def update_item(self, **kwargs):
        self.update_calls.append(kwargs)


class OutboxRelayTests(unittest.TestCase):
    def test_publishes_tenant_created_event_and_marks_published(self) -> None:
        module = _load_outbox_relay_module()
        sqs = FakeSqs()
        table = FakeOutboxTable()
        module._sqs = sqs
        module._outbox_table = table

        result = module.handler(_stream_event(_pending_item()), LambdaContext())

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sqs.sent_messages), 1)
        self.assertEqual(sqs.sent_messages[0]["QueueUrl"], "https://sqs.example/tenant-onboarding")
        self.assertIn(":published", table.update_calls[0]["ExpressionAttributeValues"])

    def test_marks_unrouted_event_as_skipped_without_sqs_publish(self) -> None:
        module = _load_outbox_relay_module()
        sqs = FakeSqs()
        table = FakeOutboxTable()
        module._sqs = sqs
        module._outbox_table = table

        result = module.handler(_stream_event(_pending_item("TenantUpdatedEvent")), LambdaContext())

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(sqs.sent_messages, [])
        self.assertIn(":skipped", table.update_calls[0]["ExpressionAttributeValues"])

    def test_returns_sequence_number_as_partial_failure_identifier(self) -> None:
        module = _load_outbox_relay_module()
        module._sqs = FakeSqs(fail=True)
        module._outbox_table = FakeOutboxTable()

        result = module.handler(_stream_event(_pending_item(), "seq-failed"), LambdaContext())

        self.assertEqual(result, {"batchItemFailures": [{"itemIdentifier": "seq-failed"}]})


if __name__ == "__main__":
    unittest.main()
