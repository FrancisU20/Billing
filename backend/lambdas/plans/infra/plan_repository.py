from __future__ import annotations

"""
PlanRepository — DynamoDB `plans` table.

PK:  id   (auto-generated UUID)
GSI: slug-index → PK=slug (slug lookup for public routes)

Slug uniqueness is enforced with a transactional lock item:
    id = "PLAN_SLUG#{slug}"

The GSI is for lookup only; it is not a uniqueness mechanism.
"""

from datetime import datetime
from decimal import Decimal

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from lambdas._base.idempotency import (
    IdempotencyContext,
    completion_transact_item,
    mark_completed,
)
from lambdas.plans.domain.errors import PlanNotFoundError, PlanSlugExistsError
from lambdas.plans.domain.plan import Plan
from lambdas.plans.domain.repositories.i_plan_repository import IPlanRepository
from shared.audit.writer import audit_item, audit_put_transact_item
from shared.errors import DatabaseError, OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoPlanRepository(IPlanRepository):
    def __init__(self, table, audit_table=None) -> None:
        self._table = table
        self._audit_table = audit_table

    # ── reads ─────────────────────────────────────────────────────────────────

    def get_by_id(self, plan_id: str) -> Plan:
        try:
            response = self._table.get_item(Key={"id": plan_id})
        except ClientError as exc:
            _log.error("DynamoDB get_item error", error=str(exc))
            raise DatabaseError() from exc

        item = response.get("Item")
        if not item or item.get("entity_type", "PLAN") != "PLAN":
            raise PlanNotFoundError()
        return self._from_item(item)

    def get_by_slug(self, slug: str) -> Plan:
        try:
            response = self._table.query(
                IndexName="slug-index",
                KeyConditionExpression=Key("slug").eq(slug),
                Limit=1,
            )
        except ClientError as exc:
            _log.error("DynamoDB slug-index query error", error=str(exc))
            raise DatabaseError() from exc

        items = [
            item for item in response.get("Items", []) if item.get("entity_type", "PLAN") == "PLAN"
        ]
        if not items:
            raise PlanNotFoundError()
        return self._from_item(items[0])

    def list(
        self,
        *,
        status: str | None = None,
        slug: str | None = None,
        q: str | None = None,
        limit_cycle: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> list[Plan]:
        filters = _PlanListFilters(
            status=status,
            slug=slug,
            q=q,
            limit_cycle=limit_cycle,
            created_from=created_from,
            created_to=created_to,
        )

        items: list[dict] = []
        kwargs: dict = {"FilterExpression": filters.to_dynamo_filter()}
        try:
            while True:
                response = self._table.scan(**kwargs)
                items.extend(response.get("Items", []))
                last_key = response.get("LastEvaluatedKey")
                if not last_key:
                    break
                kwargs["ExclusiveStartKey"] = last_key
        except ClientError as exc:
            _log.error("DynamoDB scan error", error=str(exc))
            raise DatabaseError() from exc

        plans = [
            self._from_item(item) for item in items if item.get("entity_type", "PLAN") == "PLAN"
        ]
        return [plan for plan in plans if filters.matches(plan)]

    # ── writes ────────────────────────────────────────────────────────────────

    def save(self, plan: Plan) -> None:
        self.commit(
            plan=plan,
            user_id=plan.updated_by or plan.created_by,
            action="SAVE",
            idempotency=None,
            response=None,
        )

    def commit(
        self,
        *,
        plan: Plan,
        user_id: str,
        action: str,
        idempotency: IdempotencyContext | None,
        response: dict | None,
    ) -> None:
        item = self._to_item(plan)
        old_raw = self._get_raw(plan.id)
        is_create = old_raw is None and plan.version == 1
        transact_items: list[dict] = []

        if is_create:
            transact_items.extend(self._create_items(plan, item, user_id))
        else:
            transact_items.append(self._update_item(plan, item))

        if idempotency is not None:
            if response is None:
                raise ValueError("response is required to complete idempotency")
            transact_items.append(completion_transact_item(idempotency, response))

        if self._audit_table:
            transact_items.append(
                audit_put_transact_item(
                    self._audit_table.table_name,
                    audit_item(
                        pk="AUDIT#PLAN",
                        entity_type="PLAN",
                        entity_id=plan.id,
                        action=action,
                        changed_by=user_id,
                        before=old_raw,
                        after=item,
                    ),
                )
            )

        self._transact_write(transact_items, idempotency, is_create)

    # ── internal helpers ──────────────────────────────────────────────────────

    def _get_raw(self, plan_id: str) -> dict | None:
        try:
            response = self._table.get_item(Key={"id": plan_id})
        except ClientError as exc:
            _log.error("DynamoDB get_item error", error=str(exc))
            raise DatabaseError() from exc
        return response.get("Item")

    def _create_items(self, plan: Plan, item: dict, user_id: str) -> list[dict]:
        return [
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": self._slug_lock_item(plan, user_id),
                    "ConditionExpression": "attribute_not_exists(#id)",
                    "ExpressionAttributeNames": {"#id": "id"},
                }
            },
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": item,
                    "ConditionExpression": "attribute_not_exists(#id)",
                    "ExpressionAttributeNames": {"#id": "id"},
                }
            },
        ]

    def _update_item(self, plan: Plan, item: dict) -> dict:
        return {
            "Put": {
                "TableName": self._table.table_name,
                "Item": item,
                "ConditionExpression": "attribute_exists(#id) AND #version = :prev",
                "ExpressionAttributeNames": {"#id": "id", "#version": "version"},
                "ExpressionAttributeValues": {":prev": plan.version - 1},
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
                if is_create:
                    slug_lock_failed = (
                        reasons and reasons[0].get("code") == "ConditionalCheckFailed"
                    )
                    plan_failed = (
                        len(reasons) > 1 and reasons[1].get("code") == "ConditionalCheckFailed"
                    )
                    if slug_lock_failed or plan_failed:
                        raise PlanSlugExistsError() from exc
                    raise DatabaseError() from exc
                raise OptimisticLockError() from exc
            _log.error("DynamoDB transact_write_items error", error=str(exc))
            raise DatabaseError() from exc

    def _slug_lock_item(self, plan: Plan, user_id: str) -> dict:
        return {
            "id": f"PLAN_SLUG#{plan.slug}",
            "entity_type": "PLAN_SLUG_LOCK",
            "plan_id": plan.id,
            "locked_slug": plan.slug,
            "created_at": plan.created_at.isoformat(),
            "created_by": user_id,
        }

    # ── serialisation ─────────────────────────────────────────────────────────

    def _to_item(self, plan: Plan) -> dict:
        return {
            "entity_type": "PLAN",
            "id": plan.id,
            "slug": plan.slug,
            "name": plan.name,
            "description": plan.description,
            "monthly_price": str(plan.monthly_price),
            "annual_price": str(plan.annual_price),
            "document_limit": plan.document_limit,
            "limit_cycle": plan.limit_cycle,
            "max_locations": plan.max_locations,
            "max_emission_points": plan.max_emission_points,
            "max_users": plan.max_users,
            "pruebas_monthly_docs_limit": plan.pruebas_monthly_docs_limit,
            "pruebas_monthly_bulk_limit": plan.pruebas_monthly_bulk_limit,
            "dedicated_queue": plan.dedicated_queue,
            "self_service": plan.self_service,
            "includes_credit_notes": plan.includes_credit_notes,
            "includes_withholdings": plan.includes_withholdings,
            "includes_delivery_notes": plan.includes_delivery_notes,
            "includes_api": plan.includes_api,
            "active": plan.active,
            "order": plan.order,
            "version": plan.version,
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
            "created_by": plan.created_by,
            "updated_by": plan.updated_by,
        }

    def _from_item(self, item: dict) -> Plan:
        return Plan(
            id=item["id"],
            slug=item.get("slug", ""),
            name=item.get("name", ""),
            description=item.get("description", ""),
            monthly_price=Decimal(str(item.get("monthly_price", "0.00"))),
            annual_price=Decimal(str(item.get("annual_price", "0.00"))),
            document_limit=int(item.get("document_limit", 0)),
            limit_cycle=item.get("limit_cycle", "month"),
            max_locations=int(item.get("max_locations", 1)),
            max_emission_points=int(item.get("max_emission_points", 1)),
            max_users=int(item.get("max_users", 1)),
            pruebas_monthly_docs_limit=int(item.get("pruebas_monthly_docs_limit", 0)),
            pruebas_monthly_bulk_limit=int(item.get("pruebas_monthly_bulk_limit", 0)),
            dedicated_queue=bool(item.get("dedicated_queue", False)),
            self_service=bool(item.get("self_service", True)),
            includes_credit_notes=bool(item.get("includes_credit_notes", True)),
            includes_withholdings=bool(item.get("includes_withholdings", True)),
            includes_delivery_notes=bool(item.get("includes_delivery_notes", True)),
            includes_api=bool(item.get("includes_api", False)),
            active=bool(item.get("active", True)),
            order=int(item.get("order", 0)),
            version=int(item.get("version", 1)),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            created_by=item.get("created_by", ""),
            updated_by=item.get("updated_by", ""),
        )


class _PlanListFilters:
    def __init__(
        self,
        *,
        status: str | None,
        slug: str | None,
        q: str | None,
        limit_cycle: str | None,
        created_from: str | None,
        created_to: str | None,
    ) -> None:
        self.active = {"active": True, "inactive": False}.get(status)
        self.slug = slug.strip().lower() if slug else None
        self.needle = q.strip().lower() if q else ""
        self.limit_cycle = limit_cycle
        self.created_from = created_from
        self.created_to = created_to

    def to_dynamo_filter(self):
        filter_expr = Attr("entity_type").not_exists() | Attr("entity_type").eq("PLAN")
        if self.active is not None:
            filter_expr = filter_expr & Attr("active").eq(self.active)
        if self.slug:
            filter_expr = filter_expr & Attr("slug").eq(self.slug)
        if self.limit_cycle:
            filter_expr = filter_expr & Attr("limit_cycle").eq(self.limit_cycle)
        if self.created_from:
            filter_expr = filter_expr & Attr("created_at").gte(self.created_from)
        if self.created_to:
            filter_expr = filter_expr & Attr("created_at").lte(self.created_to)
        return filter_expr

    def matches(self, plan: Plan) -> bool:
        if self.active is not None and plan.active != self.active:
            return False
        if self.slug and plan.slug.lower() != self.slug:
            return False
        if self.limit_cycle and plan.limit_cycle != self.limit_cycle:
            return False
        created_at = plan.created_at.isoformat()
        if self.created_from and created_at < self.created_from:
            return False
        if self.created_to and created_at > self.created_to:
            return False
        if not self.needle:
            return True
        return (
            self.needle in plan.name.lower()
            or self.needle in plan.description.lower()
            or self.needle in plan.slug.lower()
        )
