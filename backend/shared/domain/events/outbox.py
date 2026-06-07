from __future__ import annotations

"""Helpers to persist DomainEvents in a transactional DynamoDB outbox."""

import json
from datetime import UTC, datetime

from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.publisher import event_payload

_OUTBOX_TTL_SECONDS = 30 * 24 * 60 * 60


def outbox_item(event: DomainEvent, source: str) -> dict:
    payload = event_payload(event)
    now_dt = datetime.now(UTC)
    now = now_dt.isoformat()
    return {
        "id": event.event_id,
        "status": "PENDING",
        "event_type": event.event_type,
        "source": source,
        "payload": json.dumps(payload, default=str),
        "created_at": now,
        "updated_at": now,
        "attempts": 0,
        "ttl": int(now_dt.timestamp()) + _OUTBOX_TTL_SECONDS,
    }


def outbox_put_transact_item(table_name: str, event: DomainEvent, source: str) -> dict:
    return {
        "Put": {
            "TableName": table_name,
            "Item": outbox_item(event, source),
            "ConditionExpression": "attribute_not_exists(#id)",
            "ExpressionAttributeNames": {"#id": "id"},
        }
    }
