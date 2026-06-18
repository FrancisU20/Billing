from __future__ import annotations

import json

import boto3

from lambdas.invoice_processor.ports import IQueuePublisher
from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.publisher import EventPublisher
from shared.logger import get_logger

_log = get_logger(__name__)


class SQSQueuePublisher(IQueuePublisher):
    def __init__(self, poll_queue_url: str, email_notifications_queue_url: str) -> None:
        self._poll_queue_url = poll_queue_url
        self._client = boto3.client("sqs")
        self._event_publisher = EventPublisher(queue_url=email_notifications_queue_url)

    def enqueue_poll(
        self,
        *,
        tenant_id: str,
        document_id: str,
        access_key: str,
        attempt: int,
        delay_seconds: int,
    ) -> None:
        self._client.send_message(
            QueueUrl=self._poll_queue_url,
            MessageBody=json.dumps(
                {
                    "type": "POLL",
                    "document_id": document_id,
                    "tenant_id": tenant_id,
                    "access_key": access_key,
                    "attempt": attempt,
                }
            ),
            DelaySeconds=delay_seconds,
        )
        _log.info(
            "POLL message enqueued",
            document_id=document_id,
            attempt=attempt,
            delay_seconds=delay_seconds,
        )

    def publish_event(self, event: DomainEvent) -> None:
        self._event_publisher.publish(event)
