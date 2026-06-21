from __future__ import annotations

from decimal import Decimal

from botocore.exceptions import ClientError

from lambdas.tenants.domain.dashboard_summary import PlanPricing
from lambdas.tenants.domain.repositories.i_plan_catalog import IPlanCatalog
from shared.errors import DatabaseError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoPlanCatalog(IPlanCatalog):
    """
    Validates plan existence and status directly against the plans table.
    Intentionally does NOT import from lambdas.plans.* to keep lambda
    bundles independent.
    """

    def __init__(self, plans_table) -> None:
        self._table = plans_table

    def ensure_active(self, plan_id: str) -> str:
        if not plan_id:
            raise ValidationError("plan_id es requerido")

        try:
            resp = self._table.get_item(Key={"id": plan_id})
        except ClientError as exc:
            _log.error("DynamoDB get_item error (plan catalog)", error=str(exc))
            raise DatabaseError() from exc

        item = resp.get("Item")
        if not item or item.get("entity_type", "PLAN") != "PLAN":
            raise ValidationError("plan_id inválido")

        if item.get("deleted"):
            raise ValidationError("plan_id inválido")

        if not item.get("active", True):
            raise ValidationError("plan_id no está activo")

        return item.get("limit_cycle", "month")

    def get_pricing(self, plan_ids: set[str]) -> dict[str, PlanPricing]:
        pricing: dict[str, PlanPricing] = {}
        for plan_id in plan_ids:
            try:
                resp = self._table.get_item(Key={"id": plan_id})
            except ClientError as exc:
                _log.error("DynamoDB get_item error (plan catalog pricing)", error=str(exc))
                raise DatabaseError() from exc

            item = resp.get("Item")
            if not item or item.get("entity_type", "PLAN") != "PLAN" or item.get("deleted"):
                continue

            pricing[plan_id] = PlanPricing(
                name=item.get("name", ""),
                monthly_price=Decimal(str(item.get("monthly_price", "0.00"))),
                annual_price=Decimal(str(item.get("annual_price", "0.00"))),
                limit_cycle=item.get("limit_cycle", "month"),
            )
        return pricing
