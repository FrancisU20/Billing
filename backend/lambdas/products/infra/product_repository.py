from __future__ import annotations

"""DynamoDB repository for tenant product catalog."""

from datetime import datetime

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from lambdas._base.idempotency import (
    IdempotencyContext,
    completion_transact_item,
    mark_completed,
)
from lambdas.products.domain.entity import Product
from lambdas.products.domain.enums import ProductKind, ProductStatus
from lambdas.products.domain.errors import ProductDuplicateSkuError, ProductNotFoundError
from lambdas.products.domain.repositories.i_product_repository import IProductRepository
from shared.audit.writer import audit_item, audit_put_transact_item
from shared.db.base_repository import BaseRepository
from shared.errors import DatabaseError, OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoProductRepository(BaseRepository, IProductRepository):
    _prefix = "PRODUCT"
    _lock_prefix = "PRODUCT_SKU"

    def get_by_id(self, product_id: str) -> Product:
        item = self._get_raw(product_id)
        if not item:
            raise ProductNotFoundError()
        return self._from_item(item)

    def get_by_sku(self, sku: str, exclude_id: str | None = None) -> Product | None:
        normalized = _normalize_sku_for_lookup(sku)
        try:
            response = self._table.query(
                IndexName="sku-index",
                KeyConditionExpression=(
                    Key("tenant_id").eq(self._tenant_id) & Key("sku_normalized").eq(normalized)
                ),
            )
        except ClientError as exc:
            _log.error("DynamoDB sku-index query error", error=str(exc))
            raise DatabaseError() from exc

        for item in response.get("Items", []):
            if item.get("entity_type") != "PRODUCT" or item.get("deleted"):
                continue
            if exclude_id and item.get("id") == exclude_id:
                continue
            return self._from_item(item)
        return None

    def list(
        self,
        *,
        limit: int,
        next_token: str | None,
        status: str | None = None,
        kind: str | None = None,
        q: str | None = None,
        sku: str | None = None,
    ) -> tuple[list[Product], str | None]:
        filters = _ProductListFilters(status=status, kind=kind, q=q)
        if sku:
            product = self.get_by_sku(sku.strip().upper())
            if not product:
                return [], None
            if not filters.matches(product):
                return [], None
            return [product], None

        cursor = next_token
        products: list[Product] = []
        while len(products) < limit:
            items, cursor = self._list_raw(
                limit=limit - len(products),
                next_token=cursor,
                extra_filter=filters.to_dynamo_filter(),
            )
            for item in items:
                product = self._from_item(item)
                if not filters.matches(product):
                    continue
                products.append(product)
            if cursor is None:
                break
        return products, cursor

    def count(self, status: str | None = None, kind: str | None = None) -> int:
        """Accurate only when `q`/`sku` are not in play — those are matched in
        Python, not in DynamoDB."""
        filters = _ProductListFilters(status=status, kind=kind, q=None)
        return self._count_raw(filters.to_dynamo_filter())

    def commit(
        self,
        *,
        product: Product,
        user_id: str,
        action: str,
        idempotency: IdempotencyContext | None,
        response: dict | None,
    ) -> None:
        item = self._to_item(product)
        old_raw = self._raw_by_key(product.id)
        is_create = old_raw is None and product.version == 1

        if is_create:
            transact_items = self._create_items(product, item)
        else:
            transact_items = self._update_items(product, item, old_raw)

        if idempotency is not None:
            if response is None:
                raise ValueError("response is required to complete idempotency")
            transact_items.append(completion_transact_item(idempotency, response))

        if self._audit_table:
            transact_items.append(
                audit_put_transact_item(
                    self._audit_table.table_name,
                    audit_item(
                        pk=f"AUDIT#{self._tenant_id}",
                        entity_type="PRODUCT",
                        entity_id=product.id,
                        action=action,
                        changed_by=user_id,
                        before=old_raw,
                        after=item,
                    ),
                )
            )

        self._transact_write(transact_items, idempotency, is_create)

    def _raw_by_key(self, product_id: str) -> dict | None:
        try:
            response = self._table.get_item(Key={"pk": self._pk(), "sk": self._sk(product_id)})
            return response.get("Item")
        except ClientError as exc:
            _log.error("DynamoDB get_item error", error=str(exc))
            raise DatabaseError() from exc

    def _create_items(self, product: Product, item: dict) -> list[dict]:
        return [
            self._put_lock_item(product),
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": item,
                    "ConditionExpression": "attribute_not_exists(#pk)",
                    "ExpressionAttributeNames": {"#pk": "pk"},
                }
            },
        ]

    def _update_items(self, product: Product, item: dict, old_raw: dict | None) -> list[dict]:
        if old_raw is None:
            raise ProductNotFoundError()

        items: list[dict] = []
        old_sku = old_raw.get("sku_normalized")
        sku_changed = old_sku != product.sku_normalized

        if product.deleted and old_sku:
            items.append(self._delete_lock_item(old_sku, product.id))
        elif sku_changed and not product.deleted:
            items.append(self._put_lock_item(product))
            if old_sku:
                items.append(self._delete_lock_item(old_sku, product.id))

        items.append(
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": item,
                    "ConditionExpression": "attribute_exists(#pk) AND #version = :prev",
                    "ExpressionAttributeNames": {"#pk": "pk", "#version": "version"},
                    "ExpressionAttributeValues": {":prev": product.version - 1},
                }
            }
        )
        return items

    def _put_lock_item(self, product: Product) -> dict:
        return {
            "Put": {
                "TableName": self._table.table_name,
                "Item": self._sku_lock_item(product),
                "ConditionExpression": "attribute_not_exists(#pk)",
                "ExpressionAttributeNames": {"#pk": "pk"},
            }
        }

    def _delete_lock_item(self, sku_normalized: str, product_id: str) -> dict:
        return {
            "Delete": {
                "TableName": self._table.table_name,
                "Key": {"pk": self._pk(), "sk": self._lock_sk(sku_normalized)},
                "ConditionExpression": "attribute_not_exists(#pk) OR #product_id = :product_id",
                "ExpressionAttributeNames": {"#pk": "pk", "#product_id": "product_id"},
                "ExpressionAttributeValues": {":product_id": product_id},
            }
        }

    def _transact_write(
        self,
        transact_items: list[dict],
        idempotency: IdempotencyContext | None,
        is_create: bool,
    ) -> None:
        try:
            self._table.meta.client.transact_write_items(TransactItems=transact_items)
            if idempotency is not None:
                mark_completed()
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("TransactionCanceledException", "ConditionalCheckFailedException"):
                reasons = [
                    {"code": r.get("Code", "None"), "msg": r.get("Message", "")}
                    for r in exc.response.get("CancellationReasons", [])
                ]
                _log.error(
                    "DynamoDB transact_write_items cancelled",
                    is_create=is_create,
                    reasons=reasons,
                )
                if self._sku_lock_failed(transact_items, reasons, is_create):
                    raise ProductDuplicateSkuError() from exc
                raise OptimisticLockError() from exc
            _log.error("DynamoDB transact_write_items error", error=str(exc))
            raise DatabaseError() from exc

    def _sku_lock_failed(
        self,
        transact_items: list[dict],
        reasons: list[dict],
        is_create: bool,
    ) -> bool:
        if not reasons:
            return is_create
        for index, reason in enumerate(reasons):
            if reason.get("code") != "ConditionalCheckFailed":
                continue
            if index >= len(transact_items):
                continue
            put = transact_items[index].get("Put")
            if put and put.get("Item", {}).get("entity_type") == "PRODUCT_SKU_LOCK":
                return True
        return False

    def _lock_sk(self, sku_normalized: str) -> str:
        return f"{self._lock_prefix}#{sku_normalized}"

    def _sku_lock_item(self, product: Product) -> dict:
        return {
            "pk": self._pk(),
            "sk": self._lock_sk(product.sku_normalized),
            "entity_type": "PRODUCT_SKU_LOCK",
            "product_id": product.id,
            "locked_sku": product.sku_normalized,
            "created_at": product.created_at.isoformat(),
            "created_by": product.created_by,
        }

    def _to_item(self, product: Product) -> dict:
        return {
            "entity_type": "PRODUCT",
            "pk": self._pk(),
            "sk": self._sk(product.id),
            "id": product.id,
            "tenant_id": product.tenant_id,
            "sku": product.sku,
            "sku_normalized": product.sku_normalized,
            "name": product.name,
            "description": product.description,
            "kind": product.kind.value,
            "unit": product.unit,
            "unit_price": str(product.unit_price),
            "discount_percentage": (
                str(product.discount_percentage)
                if product.discount_percentage is not None
                else None
            ),
            "iva_rate": product.iva_rate,
            "stock_enabled": product.stock_enabled,
            "stock_quantity": (
                str(product.stock_quantity) if product.stock_quantity is not None else None
            ),
            "low_stock_threshold": (
                str(product.low_stock_threshold)
                if product.low_stock_threshold is not None
                else None
            ),
            "status": product.status.value,
            "version": product.version,
            "deleted": product.deleted,
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat(),
            "created_by": product.created_by,
            "updated_by": product.updated_by,
            "deleted_at": product.deleted_at.isoformat() if product.deleted_at else None,
            "deleted_by": product.deleted_by,
        }

    def _from_item(self, item: dict) -> Product:
        from decimal import Decimal

        return Product(
            id=item["id"],
            tenant_id=item["tenant_id"],
            sku=item["sku"],
            sku_normalized=item.get("sku_normalized", item["sku"]),
            name=item["name"],
            description=item.get("description", ""),
            kind=ProductKind(item.get("kind", "PRODUCT")),
            unit=item.get("unit", "unit"),
            unit_price=Decimal(str(item["unit_price"])),
            discount_percentage=(
                Decimal(str(item["discount_percentage"]))
                if item.get("discount_percentage") is not None
                else None
            ),
            iva_rate=item.get("iva_rate", "15"),
            stock_enabled=bool(item.get("stock_enabled", False)),
            stock_quantity=(
                Decimal(str(item["stock_quantity"]))
                if item.get("stock_quantity") is not None
                else None
            ),
            low_stock_threshold=(
                Decimal(str(item["low_stock_threshold"]))
                if item.get("low_stock_threshold") is not None
                else None
            ),
            status=ProductStatus(item.get("status", "ACTIVE")),
            version=item.get("version", 1),
            deleted=item.get("deleted", False),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            created_by=item.get("created_by", ""),
            updated_by=item.get("updated_by", ""),
            deleted_at=datetime.fromisoformat(item["deleted_at"])
            if item.get("deleted_at")
            else None,
            deleted_by=item.get("deleted_by"),
        )


class _ProductListFilters:
    def __init__(self, *, status: str | None, kind: str | None, q: str | None) -> None:
        self.status = status
        self.kind = kind
        self.needle = q.strip().lower() if q else ""

    def to_dynamo_filter(self):
        filter_expr = Attr("entity_type").eq("PRODUCT")
        if self.status:
            filter_expr = filter_expr & Attr("status").eq(self.status)
        if self.kind:
            filter_expr = filter_expr & Attr("kind").eq(self.kind)
        return filter_expr

    def matches(self, product: Product) -> bool:
        if self.status and product.status.value != self.status:
            return False
        if self.kind and product.kind.value != self.kind:
            return False
        if not self.needle:
            return True
        return (
            self.needle in product.sku.lower()
            or self.needle in product.name.lower()
            or self.needle in product.description.lower()
        )


def _normalize_sku_for_lookup(value: str) -> str:
    return (value or "").strip().upper()
