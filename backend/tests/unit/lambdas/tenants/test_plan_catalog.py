from __future__ import annotations

import unittest
from decimal import Decimal

from lambdas.tenants.infra.plan_catalog import DynamoPlanCatalog


class FakeTable:
    def __init__(self, items_by_id: dict[str, dict]) -> None:
        self.items_by_id = items_by_id
        self.get_item_calls: list[str] = []

    def get_item(self, **kwargs) -> dict:
        plan_id = kwargs["Key"]["id"]
        self.get_item_calls.append(plan_id)
        item = self.items_by_id.get(plan_id)
        return {"Item": item} if item else {}


class PlanCatalogGetPricingTests(unittest.TestCase):
    def test_returns_pricing_for_existing_active_plans(self) -> None:
        table = FakeTable(
            {
                "uuid-basic": {
                    "id": "uuid-basic",
                    "entity_type": "PLAN",
                    "name": "Básico",
                    "monthly_price": "10.00",
                    "annual_price": "100.00",
                    "limit_cycle": "month",
                    "deleted": False,
                },
            }
        )
        catalog = DynamoPlanCatalog(table)

        pricing = catalog.get_pricing({"uuid-basic", "uuid-missing"})

        self.assertIn("uuid-basic", pricing)
        self.assertEqual(pricing["uuid-basic"].name, "Básico")
        self.assertEqual(pricing["uuid-basic"].monthly_price, Decimal("10.00"))
        self.assertEqual(pricing["uuid-basic"].annual_price, Decimal("100.00"))
        self.assertEqual(pricing["uuid-basic"].limit_cycle, "month")
        self.assertNotIn("uuid-missing", pricing)

    def test_skips_deleted_plans(self) -> None:
        table = FakeTable(
            {
                "uuid-old": {
                    "id": "uuid-old",
                    "entity_type": "PLAN",
                    "name": "Viejo",
                    "monthly_price": "5.00",
                    "annual_price": "50.00",
                    "limit_cycle": "month",
                    "deleted": True,
                },
            }
        )
        catalog = DynamoPlanCatalog(table)

        pricing = catalog.get_pricing({"uuid-old"})

        self.assertEqual(pricing, {})


if __name__ == "__main__":
    unittest.main()
