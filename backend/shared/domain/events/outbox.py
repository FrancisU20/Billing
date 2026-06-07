"""Helpers para guardar DomainEvents en outbox transaccional DynamoDB."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from boto3.dynamodb.types import TypeSerializer

from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.publisher import event_payload

_serializer = TypeSerializer()
_OUTBOX_TTL_SECONDS = 30 * 24 * 60 * 60


def _serialize(item: dict) -> dict:
    return {key: _serializer.serialize(value) for key, value in item.items()}


def outbox_item(event: DomainEvent, source: str) -> dict:
    payload = event_payload(event)
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    return {
        "id":          event.event_id,
        "status":      "PENDING",
        "event_type":  event.event_type,
        "source":      source,
        "payload":     json.dumps(payload, default=str),
        "created_at":  now,
        "updated_at":  now,
        "attempts":    0,
        "ttl":         int(now_dt.timestamp()) + _OUTBOX_TTL_SECONDS,
    }


def outbox_put_transact_item(table_name: str, event: DomainEvent, source: str) -> dict:
    return {
        "Put": {
            "TableName": table_name,
            "Item": _serialize(outbox_item(event, source)),
            "ConditionExpression": "attribute_not_exists(id)",
        }
    }
