"""
Publicador de eventos de dominio → SQS.

Uso en handler.py:
    publisher = EventPublisher(queue_url=os.environ["EVENTS_QUEUE_URL"])
    result, events = use_case.execute(command)
    publisher.publish_all(events)

El cliente SQS se inicializa fuera del handler (cold start optimization).
"""
from __future__ import annotations

import dataclasses
import json

import boto3

from shared.domain.events.domain_event import DomainEvent
from shared.logger import get_logger

_log = get_logger(__name__)


def event_payload(event: DomainEvent) -> dict:
    all_fields = dataclasses.asdict(event)
    data = {
        k: v for k, v in all_fields.items()
        if k not in ("event_id", "occurred_at")
    }
    return {
        "event_type":  event.event_type,
        "event_id":    event.event_id,
        "occurred_at": event.occurred_at.isoformat(),
        "data":        data,
    }


class EventPublisher:
    def __init__(self, queue_url: str) -> None:
        self._queue_url = queue_url
        self._client    = None

    def _sqs(self):
        if self._client is None:
            self._client = boto3.client("sqs")
        return self._client

    def publish(self, event: DomainEvent) -> None:
        if not self._queue_url:
            # Local dev o workers desactivados — solo loguear
            _log.debug("events queue sin URL — evento omitido", event_type=event.event_type)
            return

        payload = event_payload(event)
        self._sqs().send_message(
            QueueUrl    = self._queue_url,
            MessageBody = json.dumps(payload, default=str),
            MessageAttributes={
                "event_type": {
                    "StringValue": event.event_type,
                    "DataType":    "String",
                }
            },
        )
        _log.info("domain event published", event_type=event.event_type, event_id=event.event_id)

    def publish_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            self.publish(event)
