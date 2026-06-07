"""Centralized construction of audit records."""
from __future__ import annotations

from datetime import datetime, timezone

from boto3.dynamodb.types import TypeSerializer

_serializer = TypeSerializer()


def _serialize(item: dict) -> dict:
    return {key: _serializer.serialize(value) for key, value in item.items()}


def audit_item(
    *,
    pk: str,
    entity_type: str,
    entity_id: str,
    action: str,
    changed_by: str,
    before: dict | None,
    after: dict | None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "pk":          pk,
        "sk":          f"{now}#{action}#{entity_id}",
        "entity_id":   entity_id,
        "entity_type": entity_type,
        "action":      action,
        "changed_by":  changed_by,
        "before":      before or {},
        "after":       after or {},
        "created_at":  now,
    }


def audit_put_transact_item(table_name: str, item: dict) -> dict:
    return {
        "Put": {
            "TableName": table_name,
            "Item": _serialize(item),
        }
    }
