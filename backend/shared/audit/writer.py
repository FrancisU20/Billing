from __future__ import annotations

"""Centralized construction of audit records."""

from datetime import UTC, datetime

# SRI Ecuador exige conservar comprobantes 7 años — los audit logs siguen el mismo criterio.
_AUDIT_TTL_SECONDS = 7 * 365 * 24 * 60 * 60


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
    now = datetime.now(UTC)
    now_iso = now.isoformat()
    return {
        "pk": pk,
        "sk": f"{now_iso}#{action}#{entity_id}",
        "entity_id": entity_id,
        "entity_type": entity_type,
        "action": action,
        "changed_by": changed_by,
        "before": before or {},
        "after": after or {},
        "created_at": now_iso,
        "ttl": int(now.timestamp()) + _AUDIT_TTL_SECONDS,
    }


def audit_put_transact_item(table_name: str, item: dict) -> dict:
    return {
        "Put": {
            "TableName": table_name,
            "Item": item,
        }
    }
