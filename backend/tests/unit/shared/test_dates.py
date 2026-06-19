from __future__ import annotations

import unittest
from datetime import UTC, datetime

from shared.dates import (
    current_ecuador_month_utc_bounds,
    format_datetime_ecuador,
    isoformat_ecuador,
    parse_date_boundary,
)


class EcuadorDatesTests(unittest.TestCase):
    def test_parse_date_boundary_expands_ecuador_day_to_utc(self) -> None:
        self.assertEqual(
            parse_date_boundary("2026-06-18", end_of_day=False),
            "2026-06-18T05:00:00+00:00",
        )
        self.assertEqual(
            parse_date_boundary("2026-06-18", end_of_day=True),
            "2026-06-19T04:59:59.999999+00:00",
        )

    def test_isoformat_ecuador_converts_utc_timestamp(self) -> None:
        value = datetime(2026, 6, 19, 0, 4, tzinfo=UTC)
        self.assertEqual(isoformat_ecuador(value), "2026-06-18T19:04:00-05:00")
        self.assertEqual(format_datetime_ecuador(value), "18-06-2026 19:04")

    def test_current_ecuador_month_bounds_use_local_month(self) -> None:
        value = datetime(2026, 7, 1, 1, 0, tzinfo=UTC)
        self.assertEqual(
            current_ecuador_month_utc_bounds(value),
            ("2026-06-01T05:00:00+00:00", "2026-07-01T04:59:59.999999+00:00"),
        )
