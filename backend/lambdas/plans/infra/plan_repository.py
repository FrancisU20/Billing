"""
PlanRepository — DynamoDB `plans` table.

PK:  id   (auto-generated UUID)
GSI: slug-index → PK=slug (slug lookup for public routes)

No pagination — the table never exceeds ~10 items.
"""
from __future__ import annotations

from datetime import datetime

from boto3.dynamodb.conditions import Attr, Key

from lambdas.plans.domain.errors import PlanNotFoundError
from lambdas.plans.domain.plan import Plan
from lambdas.plans.domain.repositories.i_plan_repository import IPlanRepository
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoPlanRepository(IPlanRepository):
    def __init__(self, table) -> None:
        self._table = table

    def get_by_id(self, plan_id: str) -> Plan:
        response = self._table.get_item(Key={"id": plan_id})
        item     = response.get("Item")
        if not item:
            raise PlanNotFoundError()
        return self._from_item(item)

    def get_by_slug(self, slug: str) -> Plan:
        response = self._table.query(
            IndexName              = "slug-index",
            KeyConditionExpression = Key("slug").eq(slug),
            Limit                  = 1,
        )
        items = response.get("Items", [])
        if not items:
            raise PlanNotFoundError()
        return self._from_item(items[0])

    def save(self, plan: Plan) -> None:
        self._table.put_item(Item=self._to_item(plan))

    def list(self, active_only: bool = False) -> list[Plan]:
        kwargs: dict = {}
        if active_only:
            kwargs["FilterExpression"] = Attr("active").eq(True)
        response = self._table.scan(**kwargs)
        return [self._from_item(i) for i in response.get("Items", [])]

    # ── serialisation ─────────────────────────────────────────────────────────

    def _to_item(self, plan: Plan) -> dict:
        return {
            "id":                    plan.id,
            "slug":                  plan.slug,
            "name":                  plan.name,
            "description":           plan.description,
            "monthly_price":         str(plan.monthly_price),
            "annual_price":          str(plan.annual_price),
            "document_limit":        plan.document_limit,
            "limit_cycle":           plan.limit_cycle,
            "max_locations":         plan.max_locations,
            "max_emission_points":   plan.max_emission_points,
            "max_users":             plan.max_users,
            "includes_credit_notes":   plan.includes_credit_notes,
            "includes_withholdings":   plan.includes_withholdings,
            "includes_delivery_notes": plan.includes_delivery_notes,
            "includes_api":          plan.includes_api,
            "active":                plan.active,
            "order":                 plan.order,
            "version":               plan.version,
            "created_at":            plan.created_at.isoformat(),
            "updated_at":            plan.updated_at.isoformat(),
            "created_by":            plan.created_by,
            "updated_by":            plan.updated_by,
        }

    def _from_item(self, item: dict) -> Plan:
        return Plan(
            id                   = item["id"],
            slug                 = item.get("slug", ""),
            name                 = item.get("name", ""),
            description          = item.get("description", ""),
            monthly_price        = float(item.get("monthly_price", 0)),
            annual_price         = float(item.get("annual_price", 0)),
            document_limit       = int(item.get("document_limit", 0)),
            limit_cycle          = item.get("limit_cycle", "month"),
            max_locations        = int(item.get("max_locations", 1)),
            max_emission_points  = int(item.get("max_emission_points", 1)),
            max_users            = int(item.get("max_users", 1)),
            includes_credit_notes   = bool(item.get("includes_credit_notes", True)),
            includes_withholdings   = bool(item.get("includes_withholdings", True)),
            includes_delivery_notes = bool(item.get("includes_delivery_notes", True)),
            includes_api         = bool(item.get("includes_api", False)),
            active               = bool(item.get("active", True)),
            order                = int(item.get("order", 0)),
            version              = int(item.get("version", 1)),
            created_at           = datetime.fromisoformat(item["created_at"]),
            updated_at           = datetime.fromisoformat(item["updated_at"]),
            created_by           = item.get("created_by", ""),
            updated_by           = item.get("updated_by", ""),
        )
