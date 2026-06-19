from __future__ import annotations

import unittest
from decimal import Decimal

from lambdas.invoice_processor.ride_builder import _discount_cell, build_ride_pdf
from tests.unit.lambdas.invoice_processor.fixtures import (
    make_document,
    make_invoice_tenant,
    make_line,
)


class DiscountCellTests(unittest.TestCase):
    def test_no_discount_renders_dash(self) -> None:
        line = make_line(discount=Decimal("0.00"))

        self.assertEqual(_discount_cell(line), "—")

    def test_renders_absolute_amount_and_percentage(self) -> None:
        # 2 x 10.00 = 20.00 gross; 5.00 discount = 25.00%
        line = make_line(
            quantity=Decimal("2"),
            unit_price=Decimal("10.00"),
            discount=Decimal("5.00"),
        )

        self.assertEqual(_discount_cell(line), "$5.00 (25.00%)")

    def test_falls_back_to_amount_only_when_gross_is_zero(self) -> None:
        line = make_line(quantity=Decimal("0"), unit_price=Decimal("0.00"), discount=Decimal("0"))
        line.discount = Decimal("1.00")  # pathological, just guards against ZeroDivisionError

        self.assertEqual(_discount_cell(line), "$1.00")


class BuildRidePdfTests(unittest.TestCase):
    def test_builds_pdf_bytes_for_a_line_with_discount(self) -> None:
        document = make_document(
            lines=[
                make_line(
                    quantity=Decimal("2"),
                    unit_price=Decimal("10.00"),
                    discount=Decimal("4.00"),
                    subtotal=Decimal("16.00"),
                )
            ]
        )
        tenant = make_invoice_tenant()

        pdf_bytes = build_ride_pdf(document, tenant)

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 0)

    def test_builds_pdf_bytes_for_a_line_without_discount(self) -> None:
        document = make_document()
        tenant = make_invoice_tenant()

        pdf_bytes = build_ride_pdf(document, tenant)

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
