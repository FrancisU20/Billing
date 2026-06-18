from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from lambdas.documents.domain.iva_rates import iva_rate_for
from tests.unit.support import configure_unit_environment

configure_unit_environment()


class IvaRateForTests(unittest.TestCase):
    def test_returns_15_since_april_2024(self) -> None:
        self.assertEqual(iva_rate_for(date(2024, 4, 1)), Decimal("15"))
        self.assertEqual(iva_rate_for(date(2026, 6, 17)), Decimal("15"))

    def test_returns_12_jan_to_march_2024(self) -> None:
        self.assertEqual(iva_rate_for(date(2024, 1, 1)), Decimal("12"))
        self.assertEqual(iva_rate_for(date(2024, 3, 31)), Decimal("12"))

    def test_raises_for_unknown_date(self) -> None:
        with self.assertRaises(ValueError):
            iva_rate_for(date(2023, 12, 31))
