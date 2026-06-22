from __future__ import annotations

import unittest
from decimal import Decimal

from lambdas.tenants.domain.errors import TenantPlanNotSelfServiceError
from lambdas.tenants.infra.plan_catalog import DynamoPlanCatalog
from shared.errors import ValidationError


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


class PlanCatalogEnsureSelfServiceActiveTests(unittest.TestCase):
    def test_returns_plan_info_for_free_self_service_plan(self) -> None:
        table = FakeTable(
            {
                "uuid-free": {
                    "id": "uuid-free",
                    "entity_type": "PLAN",
                    "self_service": True,
                    "monthly_price": "0.00",
                    "annual_price": "0.00",
                    "limit_cycle": "month",
                },
            }
        )
        catalog = DynamoPlanCatalog(table)

        info = catalog.ensure_self_service_active("uuid-free")

        self.assertTrue(info.is_free)
        self.assertEqual(info.limit_cycle, "month")

    def test_returns_plan_info_for_paid_self_service_plan(self) -> None:
        table = FakeTable(
            {
                "uuid-basic": {
                    "id": "uuid-basic",
                    "entity_type": "PLAN",
                    "self_service": True,
                    "monthly_price": "10.00",
                    "annual_price": "100.00",
                    "limit_cycle": "month",
                },
            }
        )
        catalog = DynamoPlanCatalog(table)

        info = catalog.ensure_self_service_active("uuid-basic")

        self.assertFalse(info.is_free)

    def test_rejects_non_self_service_plan(self) -> None:
        table = FakeTable(
            {
                "uuid-enterprise": {
                    "id": "uuid-enterprise",
                    "entity_type": "PLAN",
                    "self_service": False,
                    "limit_cycle": "month",
                },
            }
        )
        catalog = DynamoPlanCatalog(table)

        with self.assertRaises(TenantPlanNotSelfServiceError):
            catalog.ensure_self_service_active("uuid-enterprise")

    def test_rejects_missing_plan(self) -> None:
        catalog = DynamoPlanCatalog(FakeTable({}))

        with self.assertRaises(ValidationError):
            catalog.ensure_self_service_active("uuid-missing")


if __name__ == "__main__":
    unittest.main()
