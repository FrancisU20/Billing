from __future__ import annotations

import unittest
from decimal import Decimal

from lambdas.onboarding.infra.plan_catalog import DynamoPlanCatalog


class FakePlansTable:
    def __init__(self, item: dict | None) -> None:
        self.item = item

    def get_item(self, **kwargs) -> dict:
        return {"Item": self.item} if self.item is not None else {}


class DynamoPlanCatalogTests(unittest.TestCase):
    def _item(self, **overrides) -> dict:
        item = {
            "id": "plan-1",
            "entity_type": "PLAN",
            "active": True,
            "deleted": False,
            "self_service": True,
            "limit_cycle": "month",
            "monthly_price": Decimal("0.00"),
            "annual_price": Decimal("0.00"),
            "name": "Free",
        }
        item.update(overrides)
        return item

    def test_marks_zero_prices_as_free(self) -> None:
        plan = DynamoPlanCatalog(FakePlansTable(self._item())).get("plan-1")

        self.assertTrue(plan.is_free)

    def test_uses_decimal_instead_of_float_for_free_plan_detection(self) -> None:
        plan = DynamoPlanCatalog(
            FakePlansTable(
                self._item(
                    monthly_price=Decimal("1E-325"),
                    annual_price=Decimal("0.00"),
                )
            )
        ).get("plan-1")

        self.assertFalse(plan.is_free)


if __name__ == "__main__":
    unittest.main()
