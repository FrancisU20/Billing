from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from lambdas.tenants.infra.payment_reader import DynamoPaymentReader


class ScanTable:
    table_name = "unit-payments"

    def __init__(self, scan_responses: list[dict]) -> None:
        self.scan_responses = scan_responses
        self.scan_calls: list[dict] = []

    def scan(self, **kwargs) -> dict:
        self.scan_calls.append(kwargs)
        return self.scan_responses.pop(0)


def _payment_item(*, amount: str, confirmed_at: str | None) -> dict:
    item = {"id": "PAYMENT#ORD-1", "amount": amount, "status": "PAID"}
    if confirmed_at:
        item["confirmed_at"] = confirmed_at
    return item


class PaymentReaderAggregateRevenueTests(unittest.TestCase):
    def test_sums_gross_amount_for_month_and_year(self) -> None:
        table = ScanTable(
            scan_responses=[
                {
                    "Items": [
                        _payment_item(amount="11.20", confirmed_at="2026-06-15T00:00:00+00:00"),
                        _payment_item(amount="5.60", confirmed_at="2026-01-10T00:00:00+00:00"),
                    ],
                    "LastEvaluatedKey": {"id": "PAYMENT#ORD-1"},
                },
                {
                    "Items": [
                        _payment_item(amount="22.40", confirmed_at="2026-06-01T12:00:00+00:00"),
                        # Unconfirmed payment (CREATED/PENDING never reach this path in
                        # practice since FilterExpression is status=PAID, but a defensive
                        # missing confirmed_at must not blow up the sum).
                        _payment_item(amount="999.00", confirmed_at=None),
                    ]
                },
            ]
        )
        repo = DynamoPaymentReader(table)

        stats = repo.aggregate_revenue(datetime(2026, 6, 20, tzinfo=UTC))

        self.assertEqual(stats.gross_this_month, Decimal("33.60"))
        self.assertEqual(stats.gross_this_year, Decimal("39.20"))
        self.assertEqual(len(table.scan_calls), 2)

    def test_empty_table_returns_zero(self) -> None:
        table = ScanTable(scan_responses=[{"Items": []}])
        repo = DynamoPaymentReader(table)

        stats = repo.aggregate_revenue(datetime(2026, 6, 20, tzinfo=UTC))

        self.assertEqual(stats.gross_this_month, Decimal("0.00"))
        self.assertEqual(stats.gross_this_year, Decimal("0.00"))

    def test_tracks_previous_period_and_daily_series(self) -> None:
        table = ScanTable(
            scan_responses=[
                {
                    "Items": [
                        # This month + within the last-30-day window.
                        _payment_item(amount="10.00", confirmed_at="2026-06-15T15:00:00+00:00"),
                        # Previous month, but outside the 30-day window (too old).
                        _payment_item(amount="20.00", confirmed_at="2026-05-10T15:00:00+00:00"),
                        # Previous year — not in any month bucket, not in the window.
                        _payment_item(amount="30.00", confirmed_at="2025-06-18T15:00:00+00:00"),
                        # This month + within the window, different day than the first.
                        _payment_item(amount="5.00", confirmed_at="2026-06-01T15:00:00+00:00"),
                    ]
                },
            ]
        )
        repo = DynamoPaymentReader(table)

        # Noon UTC keeps "today" unambiguous in Ecuador time (UTC-5) — avoids the
        # midnight-UTC-is-still-yesterday-in-Ecuador edge case.
        stats = repo.aggregate_revenue(datetime(2026, 6, 20, 12, 0, tzinfo=UTC))

        self.assertEqual(stats.gross_this_month, Decimal("15.00"))
        self.assertEqual(stats.gross_previous_month, Decimal("20.00"))
        self.assertEqual(stats.gross_this_year, Decimal("35.00"))
        self.assertEqual(stats.gross_previous_year, Decimal("30.00"))

        daily = {point.date: point.amount for point in stats.daily_last_30_days}
        self.assertEqual(len(daily), 30)
        self.assertEqual(daily["2026-05-22"], Decimal("0.00"))  # oldest day in the window
        self.assertEqual(daily["2026-06-20"], Decimal("0.00"))  # today
        self.assertEqual(daily["2026-06-15"], Decimal("10.00"))
        self.assertEqual(daily["2026-06-01"], Decimal("5.00"))
        # The previous-month payment (May 10) falls outside the 30-day window entirely.
        self.assertNotIn("2026-05-10", daily)
        self.assertEqual(sum(daily.values()), Decimal("15.00"))


if __name__ == "__main__":
    unittest.main()
