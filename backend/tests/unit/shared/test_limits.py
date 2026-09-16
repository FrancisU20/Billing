from __future__ import annotations

import unittest

from shared.db.limits import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT, clamp_list_limit


class ClampListLimitTests(unittest.TestCase):
    def test_below_max_unchanged(self) -> None:
        self.assertEqual(clamp_list_limit(10), 10)

    def test_at_max_unchanged(self) -> None:
        self.assertEqual(clamp_list_limit(MAX_LIST_LIMIT), MAX_LIST_LIMIT)

    def test_above_max_clamped(self) -> None:
        self.assertEqual(clamp_list_limit(MAX_LIST_LIMIT + 1), MAX_LIST_LIMIT)

    def test_large_value_clamped(self) -> None:
        self.assertEqual(clamp_list_limit(9999), MAX_LIST_LIMIT)

    def test_one_returns_one(self) -> None:
        self.assertEqual(clamp_list_limit(1), 1)

    def test_default_constant_is_less_than_max(self) -> None:
        self.assertLess(DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT)

    def test_default_not_clamped(self) -> None:
        self.assertEqual(clamp_list_limit(DEFAULT_LIST_LIMIT), DEFAULT_LIST_LIMIT)


if __name__ == "__main__":
    unittest.main()
