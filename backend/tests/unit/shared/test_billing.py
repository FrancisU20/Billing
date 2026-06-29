from __future__ import annotations

import unittest
from decimal import Decimal

from shared.billing import gross_price, plan_net_price


class BillingTests(unittest.TestCase):
    def test_plan_net_price_uses_monthly_price_by_default(self) -> None:
        self.assertEqual(plan_net_price(Decimal("5.99"), Decimal("57.00"), "month"), "5.99")

    def test_plan_net_price_uses_annual_price_for_year_cycle(self) -> None:
        self.assertEqual(plan_net_price(Decimal("5.99"), Decimal("57.00"), "year"), "57.00")

    def test_gross_price_applies_markup_with_half_up_cents(self) -> None:
        self.assertEqual(gross_price("5.99"), "6.71")


if __name__ == "__main__":
    unittest.main()
