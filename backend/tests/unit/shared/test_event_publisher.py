from __future__ import annotations

import json
import unittest
from dataclasses import dataclass

from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.publisher import DirectPublishReason, EventPublisher


@dataclass(frozen=True)
class ExampleEvent(DomainEvent):
    tenant_id: str = "tenant-1"


class FakeSqsClient:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def send_message(self, **kwargs) -> None:
        self.messages.append(kwargs)


class EventPublisherTests(unittest.TestCase):
    def test_publish_includes_direct_delivery_reason(self) -> None:
        sqs = FakeSqsClient()
        publisher = EventPublisher(
            queue_url="https://sqs.example/queue",
            reason=DirectPublishReason.POST_COMMIT_WORKER_SIDE_EFFECT,
        )
        publisher._client = sqs

        publisher.publish(ExampleEvent())

        self.assertEqual(len(sqs.messages), 1)
        message = sqs.messages[0]
        self.assertEqual(
            message["MessageAttributes"]["delivery_reason"]["StringValue"],
            "post_commit_worker_side_effect",
        )
        body = json.loads(message["MessageBody"])
        self.assertEqual(body["event_type"], "ExampleEvent")
        self.assertEqual(body["data"]["tenant_id"], "tenant-1")


if __name__ == "__main__":
    unittest.main()
