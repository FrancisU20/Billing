from __future__ import annotations

"""
Direct domain event publisher → SQS.

Use this only when the event is intentionally published outside the state-changing
DynamoDB transaction. For business events that must be committed atomically with a
DynamoDB mutation, use `shared.domain.events.outbox.outbox_put_transact_item()` instead.

Valid direct-publish cases:
- post-commit workflow side effects where the caller/worker can retry the whole step,
- non-transactional notifications,
- legacy processors whose state mutation and notification cannot share one transaction yet.

The SQS client is initialized outside the handler (cold start optimization).
"""

import dataclasses
import json
from enum import StrEnum

import boto3

from shared.domain.events.domain_event import DomainEvent
from shared.logger import get_logger

_log = get_logger(__name__)


class DirectPublishReason(StrEnum):
    NON_TRANSACTIONAL_NOTIFICATION = "non_transactional_notification"
    POST_COMMIT_WORKER_SIDE_EFFECT = "post_commit_worker_side_effect"
    LEGACY_PROCESSOR_NOTIFICATION = "legacy_processor_notification"


def _serialize_value(v: object) -> object:
    """Convert any value to a JSON-safe type (handles Enum, Decimal, datetime, dataclasses)."""
    import enum
    from datetime import datetime
    from decimal import Decimal

    if isinstance(v, enum.Enum):
        return v.value
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return {k: _serialize_value(val) for k, val in dataclasses.asdict(v).items()}
    if isinstance(v, list | tuple):
        return [_serialize_value(i) for i in v]
    if isinstance(v, dict):
        return {k: _serialize_value(val) for k, val in v.items()}
    return v


def event_payload(event: DomainEvent) -> dict:
    all_fields = dataclasses.fields(event)
    data = {
        f.name: _serialize_value(getattr(event, f.name))
        for f in all_fields
        if f.name not in ("event_id", "occurred_at")
    }
    return {
        "event_type": event.event_type,
        "event_id": event.event_id,
        "occurred_at": event.occurred_at.isoformat(),
        "data": data,
    }


class EventPublisher:
    """Fire-and-forget SQS publisher.

    Do not use for domain events that must be atomically persisted with a business write.
    Repositories should add those events to the outbox transaction instead.
    """

    def __init__(self, queue_url: str, *, reason: DirectPublishReason) -> None:
        self._queue_url = queue_url
        self._reason = reason
        self._client = None

    def _sqs(self):
        if self._client is None:
            self._client = boto3.client("sqs")
        return self._client

    def publish(self, event: DomainEvent) -> None:
        if not self._queue_url:
            # Local dev or workers disabled — just log
            _log.debug("events queue has no URL — event skipped", event_type=event.event_type)
            return

        payload = event_payload(event)
        self._sqs().send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(payload, default=str),
            MessageAttributes={
                "event_type": {
                    "StringValue": event.event_type,
                    "DataType": "String",
                },
                "delivery_reason": {
                    "StringValue": self._reason.value,
                    "DataType": "String",
                },
            },
        )
        _log.info(
            "domain event published",
            event_type=event.event_type,
            event_id=event.event_id,
            delivery_reason=self._reason.value,
        )

    def publish_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            self.publish(event)
