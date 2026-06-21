from __future__ import annotations

"""
DynamoDB plan lookup for onboarding.

Intentionally does NOT import from lambdas.plans.* to keep lambda bundles
independent (same convention as lambdas.tenants.infra.plan_catalog).
"""

from botocore.exceptions import ClientError

from lambdas.onboarding.domain.errors import PlanNotActiveError, PlanNotFoundError
from lambdas.onboarding.domain.repositories.i_plan_catalog import IPlanCatalog, PlanSummary
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoPlanCatalog(IPlanCatalog):
    def __init__(self, plans_table) -> None:
        self._table = plans_table

    def get(self, plan_id: str) -> PlanSummary:
        try:
            resp = self._table.get_item(Key={"id": plan_id})
        except ClientError as exc:
            _log.error("DynamoDB get_item error (plan catalog)", error=str(exc))
            raise DatabaseError() from exc

        item = resp.get("Item")
        if not item or item.get("entity_type", "PLAN") != "PLAN" or item.get("deleted"):
            raise PlanNotFoundError()

        if not item.get("active", True):
            raise PlanNotActiveError()

        monthly = float(item.get("monthly_price", 0) or 0)
        annual = float(item.get("annual_price", 0) or 0)
        return PlanSummary(
            id=item["id"],
            self_service=bool(item.get("self_service", True)),
            limit_cycle=item.get("limit_cycle", "month"),
            is_free=monthly == 0 and annual == 0,
            name=item.get("name", ""),
        )
