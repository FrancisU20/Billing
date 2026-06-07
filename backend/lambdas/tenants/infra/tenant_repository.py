"""
DynamoDB implementation of the Tenant repository.

Does not extend BaseRepository (which is for TenantScopedEntity).
Tenant is a GlobalEntity with its own key logic.

DynamoDB table:
    PK: id (tenant UUID)
    GSI ruc-index: PK=ruc (lookup by RUC)
    RUC uniqueness lock: id="RUC#{ruc}" in the same table

Listing: Scan with FilterExpression (acceptable — few tenants in a B2B SaaS).
"""
from __future__ import annotations

from datetime import datetime

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from lambdas._base.idempotency import (
    IdempotencyContext,
    completion_transact_item,
    mark_completed,
)
from shared.audit.writer import audit_item, audit_put_transact_item
from shared.db.paginator import decode_cursor, encode_cursor
from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.outbox import outbox_put_transact_item
from shared.errors import DatabaseError, OptimisticLockError
from shared.logger import get_logger

from lambdas.tenants.domain.enums import SriEnvironment, TenantStatus, PlanStatus
from lambdas.tenants.domain.errors import TenantNotFoundError, TenantRucAlreadyExistsError
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant

_log = get_logger(__name__)


class DynamoTenantRepository(ITenantRepository):
    def __init__(self, table, audit_table=None, outbox_table=None) -> None:
        self._table        = table
        self._audit_table  = audit_table
        self._outbox_table = outbox_table

    # ── reads ─────────────────────────────────────────────────────────────────

    def get_by_id(self, tenant_id: str) -> Tenant:
        try:
            resp = self._table.get_item(Key={"id": tenant_id})
        except ClientError as e:
            _log.error("DynamoDB get_item error", error=str(e))
            raise DatabaseError()

        item = resp.get("Item")
        if not item or item.get("deleted") or item.get("entity_type", "TENANT") != "TENANT":
            raise TenantNotFoundError()
        return self._from_item(item)

    def get_by_ruc(self, ruc: str) -> Tenant | None:
        try:
            resp = self._table.query(
                IndexName              = "ruc-index",
                KeyConditionExpression = Key("ruc").eq(ruc),
            )
        except ClientError as e:
            _log.error("DynamoDB ruc-index query error", error=str(e))
            raise DatabaseError()

        items = [
            item for item in resp.get("Items", [])
            if item.get("entity_type", "TENANT") == "TENANT"
        ]
        if not items:
            return None

        active = [item for item in items if not item.get("deleted")]
        return self._from_item((active or items)[0])

    def list(
        self,
        limit:      int,
        next_token: str | None,
        status:     str | None = None,
    ) -> tuple[list[Tenant], str | None]:
        filter_expr = Attr("deleted").eq(False)
        if status:
            filter_expr = filter_expr & Attr("status").eq(status)

        kwargs: dict = {"FilterExpression": filter_expr, "Limit": limit}
        cursor = decode_cursor(next_token)
        if cursor:
            kwargs["ExclusiveStartKey"] = cursor

        try:
            resp = self._table.scan(**kwargs)
        except ClientError as e:
            _log.error("DynamoDB scan error", error=str(e))
            raise DatabaseError()

        return (
            [self._from_item(i) for i in resp.get("Items", [])],
            encode_cursor(resp.get("LastEvaluatedKey")),
        )

    # ── writes ────────────────────────────────────────────────────────────────

    def save(self, tenant: Tenant, user_id: str) -> None:
        self.commit(
            tenant      = tenant,
            user_id     = user_id,
            action      = "SAVE",
            events      = [],
            idempotency = None,
            response    = None,
        )

    def commit(
        self,
        *,
        tenant:      Tenant,
        user_id:     str,
        action:      str,
        events:      list[DomainEvent],
        idempotency: IdempotencyContext | None,
        response:    dict | None,
    ) -> None:
        item      = self._to_item(tenant)
        old_raw   = self._get_raw(tenant.id)
        is_create = old_raw is None and tenant.version == 1
        transact_items: list[dict] = []

        if is_create:
            transact_items.extend(self._create_items(tenant, item, user_id))
        else:
            transact_items.append(self._update_item(tenant, item))

        if idempotency is not None:
            if response is None:
                raise ValueError("response is required to complete idempotency")
            transact_items.append(completion_transact_item(idempotency, response))

        if self._outbox_table:
            for event in events:
                transact_items.append(
                    outbox_put_transact_item(
                        self._outbox_table.table_name,
                        event,
                        source="tenants",
                    )
                )

        if self._audit_table:
            transact_items.append(audit_put_transact_item(
                self._audit_table.table_name,
                audit_item(
                    pk          = "AUDIT#TENANT",
                    entity_type = "TENANT",
                    entity_id   = tenant.id,
                    action      = action,
                    changed_by  = user_id,
                    before      = old_raw,
                    after       = item,
                ),
            ))

        self._transact_write(transact_items, idempotency, is_create)

    def delete(self, tenant_id: str, deleted_by: str) -> None:
        tenant = self.get_by_id(tenant_id)
        tenant.soft_delete(deleted_by)
        self.save(tenant, deleted_by)

    # ── internal helpers ──────────────────────────────────────────────────────

    def _get_raw(self, tenant_id: str) -> dict | None:
        try:
            resp = self._table.get_item(Key={"id": tenant_id})
            return resp.get("Item")
        except ClientError as e:
            _log.error("DynamoDB get_item error", error=str(e))
            raise DatabaseError()

    def _create_items(self, tenant: Tenant, item: dict, user_id: str) -> list[dict]:
        lock_item = self._ruc_lock_item(tenant, user_id)
        return [
            {
                "Put": {
                    "TableName":                self._table.table_name,
                    "Item":                     lock_item,
                    "ConditionExpression":      "attribute_not_exists(#id)",
                    "ExpressionAttributeNames": {"#id": "id"},
                }
            },
            {
                "Put": {
                    "TableName":                self._table.table_name,
                    "Item":                     item,
                    "ConditionExpression":      "attribute_not_exists(#id)",
                    "ExpressionAttributeNames": {"#id": "id"},
                }
            },
        ]

    def _update_item(self, tenant: Tenant, item: dict) -> dict:
        return {
            "Put": {
                "TableName":                self._table.table_name,
                "Item":                     item,
                "ConditionExpression":      "attribute_exists(#id) AND #version = :prev",
                "ExpressionAttributeNames": {"#id": "id", "#version": "version"},
                "ExpressionAttributeValues": {":prev": tenant.version - 1},
            }
        }

    def _transact_write(
        self,
        transact_items: list[dict],
        idempotency:    IdempotencyContext | None,
        is_create:      bool,
    ) -> None:
        try:
            self._table.meta.client.transact_write_items(TransactItems=transact_items)
            if idempotency is not None:
                mark_completed()
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("TransactionCanceledException", "ConditionalCheckFailedException"):
                reasons = [
                    {"code": r.get("Code", "None"), "msg": r.get("Message", "")}
                    for r in e.response.get("CancellationReasons", [])
                ]
                _log.error(
                    "DynamoDB transact_write_items cancelled",
                    is_create=is_create,
                    reasons=reasons,
                    error=str(e),
                )
                if is_create:
                    ruc_lock_failed = reasons and reasons[0].get("code") == "ConditionalCheckFailed"
                    tenant_failed   = len(reasons) > 1 and reasons[1].get("code") == "ConditionalCheckFailed"
                    if ruc_lock_failed or tenant_failed:
                        raise TenantRucAlreadyExistsError()
                    raise DatabaseError()
                raise OptimisticLockError()
            _log.error("DynamoDB transact_write_items error", error=str(e))
            raise DatabaseError()

    def _ruc_lock_item(self, tenant: Tenant, user_id: str) -> dict:
        return {
            "id":          f"RUC#{tenant.ruc}",
            "entity_type": "TENANT_RUC_LOCK",
            "tenant_id":   tenant.id,
            "locked_ruc":  tenant.ruc,
            "created_at":  tenant.created_at.isoformat(),
            "created_by":  user_id,
        }

    def _to_item(self, tenant: Tenant) -> dict:
        return {
            "entity_type":   "TENANT",
            "id":            tenant.id,
            "ruc":           tenant.ruc,
            "trade_name":    tenant.trade_name,
            "legal_rep_name": tenant.legal_rep_name,
            "email":         tenant.email,
            "phone":         tenant.phone,
            "address":       tenant.address,
            "sri_environment": tenant.sri_environment.value,
            "status":        tenant.status.value,
            "plan_id":       tenant.plan_id,
            "plan_status":   tenant.plan_status.value,
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            "version":       tenant.version,
            "deleted":       tenant.deleted,
            "created_at":    tenant.created_at.isoformat(),
            "updated_at":    tenant.updated_at.isoformat(),
            "created_by":    tenant.created_by,
            "updated_by":    tenant.updated_by,
            "deleted_at":    tenant.deleted_at.isoformat() if tenant.deleted_at else None,
            "deleted_by":    tenant.deleted_by,
        }

    def _from_item(self, item: dict) -> Tenant:
        return Tenant(
            id              = item["id"],
            ruc             = item["ruc"],
            trade_name      = item.get("trade_name", ""),
            legal_rep_name  = item.get("legal_rep_name", ""),
            email           = item["email"],
            phone           = item.get("phone", ""),
            address         = item.get("address", ""),
            sri_environment = SriEnvironment(item.get("sri_environment", "testing")),
            status          = TenantStatus(item.get("status", "active")),
            plan_id         = item.get("plan_id", ""),
            plan_status     = PlanStatus(item.get("plan_status", "active")),
            trial_ends_at   = datetime.fromisoformat(item["trial_ends_at"]) if item.get("trial_ends_at") else None,
            version         = item.get("version", 1),
            deleted         = item.get("deleted", False),
            created_at      = datetime.fromisoformat(item["created_at"]),
            updated_at      = datetime.fromisoformat(item["updated_at"]),
            created_by      = item.get("created_by", ""),
            updated_by      = item.get("updated_by", ""),
            deleted_at      = datetime.fromisoformat(item["deleted_at"]) if item.get("deleted_at") else None,
            deleted_by      = item.get("deleted_by"),
        )
