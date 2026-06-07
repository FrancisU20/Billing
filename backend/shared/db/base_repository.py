"""
Repositorio base DynamoDB.

Proporciona a todos los repositorios concretos:
- Aislamiento multitenant automático (PK siempre incluye tenant_id)
- Soft delete — nunca se llama delete_item directamente
- Optimistic locking con version (ConditionalExpression de boto3)
- Audit log automático en cada mutación
- Mapeo de excepciones boto3 → AppError

Convención de claves:
    PK = "TENANT#{tenant_id}"
    SK = "{PREFIX}#{entity_id}"

Cada repositorio concreto define `_prefix` y los métodos de mapeo
entidad ↔ ítem DynamoDB (_to_item / _from_item).

Nota sobre paginación y soft delete:
    DynamoDB aplica Limit ANTES de FilterExpression. Por eso el filtro
    `deleted = false` se envía como FilterExpression (no en Python),
    lo que reduce el problema pero no lo elimina completamente.
    Para listas con muchos soft-deleted, usar un GSI con deleted como
    clave de partición en fases posteriores.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from boto3.dynamodb.conditions import Attr, Key as DKey
from botocore.exceptions import ClientError

from shared.audit.writer import audit_item
from shared.db.paginator import decode_cursor, encode_cursor
from shared.domain.base_entity import TenantScopedEntity
from shared.errors import DatabaseError, OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)


class BaseRepository(ABC):
    _prefix: str = ""   # Override en subclase: "TENANT", "CLIENT", etc.

    def __init__(self, tenant_id: str, table, audit_table=None) -> None:
        if not tenant_id:
            raise ValueError("tenant_id es requerido en el repositorio")
        self._tenant_id   = tenant_id
        self._table       = table
        self._audit_table = audit_table

    # ── claves ────────────────────────────────────────────────────────────────

    def _pk(self) -> str:
        return f"TENANT#{self._tenant_id}"

    def _sk(self, entity_id: str) -> str:
        return f"{self._prefix}#{entity_id}"

    # ── operaciones base ──────────────────────────────────────────────────────

    def _get_raw(self, entity_id: str) -> dict | None:
        try:
            resp = self._table.get_item(
                Key={"pk": self._pk(), "sk": self._sk(entity_id)}
            )
            item = resp.get("Item")
            if not item or item.get("deleted"):
                return None
            return item
        except ClientError as e:
            _log.error("DynamoDB get_item error", error=str(e))
            raise DatabaseError()

    def _put_raw(
        self,
        item:      dict,
        condition: Any | None = None,
    ) -> None:
        """
        condition debe ser un objeto de boto3.dynamodb.conditions (Attr/Key),
        no un string. Ejemplo:
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
        limit:       int = 20,
        next_token:  str | None = None,
        extra_filter: Any | None = None,
    ) -> tuple[list[dict], str | None]:
        """
        extra_filter: condición Attr adicional que se combina con el filtro
        base de soft delete. Ejemplo: Attr("estado").eq("activo")
        """
        # Filtro base: excluir soft-deleted a nivel DynamoDB (no en Python)
        base_filter = Attr("deleted").eq(False)
        filter_expr = (
            base_filter & extra_filter if extra_filter is not None else base_filter
        )

        kwargs: dict[str, Any] = {
            "KeyConditionExpression": (
                DKey("pk").eq(self._pk())
                & DKey("sk").begins_with(f"{self._prefix}#")
            ),
            "FilterExpression": filter_expr,
            "Limit": limit,
        }

        cursor = decode_cursor(next_token)
        if cursor:
            kwargs["ExclusiveStartKey"] = cursor

        try:
            resp  = self._table.query(**kwargs)
            return resp.get("Items", []), encode_cursor(resp.get("LastEvaluatedKey"))
        except ClientError as e:
            _log.error("DynamoDB query error", error=str(e))
            raise DatabaseError()

    # ── audit log ─────────────────────────────────────────────────────────────

    def _audit(
        self,
        action:    str,
        entity_id: str,
        user_id:   str,
        before:    dict | None,
        after:     dict | None,
    ) -> None:
        if not self._audit_table:
            return
        try:
            self._audit_table.put_item(Item=audit_item(
                pk          = f"AUDIT#{self._tenant_id}",
                entity_type = self._prefix,
                entity_id   = entity_id,
                action      = action,
                changed_by  = user_id,
                before      = before,
                after       = after,
            ))
        except Exception as e:
            _log.warning("audit log fallido (no bloqueante)", error=str(e))

    # ── abstract ──────────────────────────────────────────────────────────────

    @abstractmethod
    def _to_item(self, entity: TenantScopedEntity) -> dict:
        """Convierte entidad de dominio → ítem DynamoDB."""

    @abstractmethod
    def _from_item(self, item: dict) -> TenantScopedEntity:
        """Convierte ítem DynamoDB → entidad de dominio."""
