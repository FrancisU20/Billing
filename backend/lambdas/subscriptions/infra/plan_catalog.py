from __future__ import annotations

"""
Local plan lookup for the subscriptions lambda.

Does NOT import from lambdas.plans.* — same convention as tenants and onboarding.
"""

from decimal import Decimal

from botocore.exceptions import ClientError

from lambdas.subscriptions.domain.errors import PlanNotFoundForPaymentError
from lambdas.subscriptions.domain.repositories.i_plan_catalog import IPlanCatalog, PlanSummary
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
        if (
            not item
            or item.get("entity_type", "PLAN") != "PLAN"
            or item.get("deleted")
            or not item.get("active", True)
        ):
            raise PlanNotFoundForPaymentError()

        monthly_price = Decimal(str(item.get("monthly_price", "0.00")))
        annual_price = Decimal(str(item.get("annual_price", "0.00")))

        return PlanSummary(
            id=item["id"],
            monthly_price=monthly_price,
            annual_price=annual_price,
            limit_cycle=item.get("limit_cycle", "month"),
            is_free=monthly_price == Decimal("0.00") and annual_price == Decimal("0.00"),
            self_service=bool(item.get("self_service", True)),
        )
