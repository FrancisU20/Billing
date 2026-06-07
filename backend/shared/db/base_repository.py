from __future__ import annotations

"""
Base DynamoDB repository.

Provides every concrete repository with:
- Automatic multitenant isolation (PK always includes tenant_id)
- Soft delete — delete_item is never called directly
- Optimistic locking via version (boto3 ConditionalExpression)
- Automatic audit log on every mutation
- boto3 exception → AppError mapping

Key convention:
    PK = "TENANT#{tenant_id}"
    SK = "{PREFIX}#{entity_id}"

Each concrete repository defines `_prefix` and the mapping methods
entity ↔ DynamoDB item (_to_item / _from_item).

Note on pagination and soft delete:
    DynamoDB applies Limit BEFORE FilterExpression. That is why the
    `deleted = false` filter is sent as a FilterExpression (not in Python),
    which mitigates the problem but does not fully eliminate it.
    For lists with many soft-deleted rows, use a GSI with `deleted` as the
    partition key in later phases.
"""

from abc import ABC, abstractmethod
from typing import Any

from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.conditions import Key as DKey
from botocore.exceptions import ClientError

from shared.audit.writer import audit_item
from shared.db.paginator import decode_cursor, encode_cursor
from shared.domain.base_entity import TenantScopedEntity
from shared.errors import DatabaseError, OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)


class BaseRepository(ABC):
    _prefix: str = ""  # Override in subclass: "TENANT", "CLIENT", etc.

    def __init__(self, tenant_id: str, table, audit_table=None) -> None:
        if not tenant_id:
            raise ValueError("tenant_id is required in the repository")
        self._tenant_id = tenant_id
        self._table = table
        self._audit_table = audit_table

    # ── keys ──────────────────────────────────────────────────────────────────

    def _pk(self) -> str:
        return f"TENANT#{self._tenant_id}"

    def _sk(self, entity_id: str) -> str:
        return f"{self._prefix}#{entity_id}"

    # ── base operations ───────────────────────────────────────────────────────

    def _get_raw(self, entity_id: str) -> dict | None:
        try:
            resp = self._table.get_item(Key={"pk": self._pk(), "sk": self._sk(entity_id)})
            item = resp.get("Item")
            if not item or item.get("deleted"):
                return None
            return item
        except ClientError as e:
            _log.error("DynamoDB get_item error", error=str(e))
            raise DatabaseError()

    def _put_raw(
        self,
        item: dict,
        condition: Any | None = None,
    ) -> None:
        """
        condition must be a boto3.dynamodb.conditions object (Attr/Key),
        not a string. Example:
            Attr("pk").not_exists() | Attr("version").eq(current_version)
        """
        kwargs: dict[str, Any] = {"Item": item}
        if condition is not None:
            kwargs["ConditionExpression"] = condition
        try:
            self._table.put_item(**kwargs)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "ConditionalCheckFailedException":
                raise OptimisticLockError()
            _log.error("DynamoDB put_item error", error=str(e))
            raise DatabaseError()

    def _list_raw(
        self,
        limit: int = 20,
        next_token: str | None = None,
        extra_filter: Any | None = None,
    ) -> tuple[list[dict], str | None]:
        """
        extra_filter: additional Attr condition combined with the base
        soft-delete filter. Example: Attr("status").eq("active")
        """
        # Base filter: exclude soft-deleted at the DynamoDB level (not in Python)
        base_filter = Attr("deleted").eq(False)
        filter_expr = base_filter & extra_filter if extra_filter is not None else base_filter

        kwargs: dict[str, Any] = {
            "KeyConditionExpression": (
                DKey("pk").eq(self._pk()) & DKey("sk").begins_with(f"{self._prefix}#")
            ),
            "FilterExpression": filter_expr,
            "Limit": limit,
        }

        cursor = decode_cursor(next_token)
        if cursor:
            kwargs["ExclusiveStartKey"] = cursor

        try:
            resp = self._table.query(**kwargs)
            return resp.get("Items", []), encode_cursor(resp.get("LastEvaluatedKey"))
        except ClientError as e:
            _log.error("DynamoDB query error", error=str(e))
            raise DatabaseError()

    # ── audit log ─────────────────────────────────────────────────────────────

    def _audit(
        self,
        action: str,
        entity_id: str,
        user_id: str,
        before: dict | None,
        after: dict | None,
    ) -> None:
        if not self._audit_table:
            return
        try:
            self._audit_table.put_item(
                Item=audit_item(
                    pk=f"AUDIT#{self._tenant_id}",
                    entity_type=self._prefix,
                    entity_id=entity_id,
                    action=action,
                    changed_by=user_id,
                    before=before,
                    after=after,
                )
            )
        except Exception as e:
            _log.warning("audit log failed (non-blocking)", error=str(e))

    # ── abstract ──────────────────────────────────────────────────────────────

    @abstractmethod
    def _to_item(self, entity: TenantScopedEntity) -> dict:
        """Convert domain entity → DynamoDB item."""

    @abstractmethod
    def _from_item(self, item: dict) -> TenantScopedEntity:
        """Convert DynamoDB item → domain entity."""
