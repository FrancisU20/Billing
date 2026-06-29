from __future__ import annotations

"""DynamoDB uniqueness lock helpers."""

from datetime import datetime
from typing import Any


def unique_lock_item(
    *,
    key: dict[str, Any],
    entity_type: str,
    owner_field: str,
    owner_id: str,
    locked_field: str,
    locked_value: str,
    created_at: datetime | str,
    created_by: str,
) -> dict[str, Any]:
    timestamp = created_at.isoformat() if isinstance(created_at, datetime) else created_at
    return {
        **key,
        "entity_type": entity_type,
        owner_field: owner_id,
        locked_field: locked_value,
        "created_at": timestamp,
        "created_by": created_by,
    }


def put_unique_lock_transact_item(
    *,
    table_name: str,
    item: dict[str, Any],
    partition_key_name: str,
) -> dict[str, Any]:
    return {
        "Put": {
            "TableName": table_name,
            "Item": item,
            "ConditionExpression": "attribute_not_exists(#lock_pk)",
            "ExpressionAttributeNames": {"#lock_pk": partition_key_name},
        }
    }


def delete_unique_lock_transact_item(
    *,
    table_name: str,
    key: dict[str, Any],
    partition_key_name: str,
    owner_field: str,
    owner_id: str,
) -> dict[str, Any]:
    return {
        "Delete": {
            "TableName": table_name,
            "Key": key,
            "ConditionExpression": "attribute_not_exists(#lock_pk) OR #owner_id = :owner_id",
            "ExpressionAttributeNames": {
                "#lock_pk": partition_key_name,
                "#owner_id": owner_field,
            },
            "ExpressionAttributeValues": {":owner_id": owner_id},
        }
    }
