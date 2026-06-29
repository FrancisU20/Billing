from __future__ import annotations

import unittest
from decimal import Decimal

from lambdas.documents.domain.entities import InvoiceLine
from lambdas.documents.domain.totals import (
    aggregate_line_totals,
    iva_amount_for_rate,
    line_gross_amount,
    line_subtotal_amount,
    line_total_amount,
    scale_credit_line_amounts,
)


def _line(**overrides) -> InvoiceLine:
    defaults = dict(
        code="P1",
        description="Producto",
        quantity=Decimal("2"),
        unit_price=Decimal("10.00"),
        discount=Decimal("0.00"),
        subtotal=Decimal("20.00"),
        iva_rate="15",
        iva_amount=Decimal("3.00"),
        total=Decimal("23.00"),
        product_id=None,
    )
    defaults.update(overrides)
    return InvoiceLine(**defaults)


class LineTotalsTests(unittest.TestCase):
    def test_line_gross_and_subtotal_are_quantized(self) -> None:
        self.assertEqual(line_gross_amount(Decimal("3"), Decimal("10.005")), Decimal("30.02"))
        self.assertEqual(
            line_subtotal_amount(Decimal("3"), Decimal("10.005"), Decimal("1.01")),
            Decimal("29.00"),
        )

    def test_iva_amount_for_configurable_15_rate(self) -> None:
        self.assertEqual(
            iva_amount_for_rate(
                subtotal=Decimal("20.00"),
                iva_rate="15",
                applicable_15_rate=Decimal("15"),
            ),
            Decimal("3.00"),
        )

    def test_iva_amount_for_fixed_5_rate(self) -> None:
        self.assertEqual(
            iva_amount_for_rate(
                subtotal=Decimal("20.00"),
                iva_rate="5",
                applicable_15_rate=Decimal("15"),
            ),
            Decimal("1.00"),
        )

    def test_iva_amount_for_zero_or_exento_rate_is_zero(self) -> None:
        self.assertEqual(
            iva_amount_for_rate(
                subtotal=Decimal("20.00"),
                iva_rate="0",
                applicable_15_rate=Decimal("15"),
            ),
            Decimal("0.00"),
        )
        self.assertEqual(
            iva_amount_for_rate(
                subtotal=Decimal("20.00"),
                iva_rate="EXENTO",
                applicable_15_rate=Decimal("15"),
            ),
            Decimal("0.00"),
        )

    def test_line_total_amount_is_quantized(self) -> None:
        self.assertEqual(line_total_amount(Decimal("20.00"), Decimal("3.001")), Decimal("23.00"))

    def test_scale_credit_line_amounts_uses_parent_line_amounts(self) -> None:
        parent = _line(
            quantity=Decimal("4"),
            discount=Decimal("2.00"),
            subtotal=Decimal("38.00"),
            iva_amount=Decimal("5.70"),
            total=Decimal("43.70"),
        )

        self.assertEqual(
            scale_credit_line_amounts(parent_line=parent, credited_quantity=Decimal("1")),
            (Decimal("0.50"), Decimal("9.50"), Decimal("1.42"), Decimal("10.92")),
        )

    def test_aggregate_line_totals_includes_zero_rate_bucket(self) -> None:
        result = aggregate_line_totals(
            [
                _line(iva_rate="15", iva_amount=Decimal("3.00"), total=Decimal("23.00")),
                _line(
                    code="P2",
                    iva_rate="5",
                    iva_amount=Decimal("1.00"),
                    total=Decimal("21.00"),
                ),
                _line(
                    code="P3",
                    iva_rate="0",
                    iva_amount=Decimal("0.00"),
                    total=Decimal("20.00"),
                ),
            ]
        )

        self.assertEqual(
            result,
            (
                Decimal("60.00"),
                Decimal("0.00"),
                Decimal("3.00"),
                Decimal("1.00"),
                Decimal("0.00"),
                Decimal("64.00"),
            ),
        )


if __name__ == "__main__":
    unittest.main()
