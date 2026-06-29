from __future__ import annotations

import unittest

from shared.search import matches_search_query, normalize_search_query


class SearchHelpersTests(unittest.TestCase):
    def test_normalize_search_query_strips_and_casefolds(self) -> None:
        self.assertEqual(normalize_search_query("  ACME  "), "acme")

    def test_normalize_search_query_returns_empty_for_missing_value(self) -> None:
        self.assertEqual(normalize_search_query(None), "")

    def test_matches_search_query_matches_any_candidate(self) -> None:
        self.assertTrue(matches_search_query("acme", "Other", "ACME Ecuador"))

    def test_matches_search_query_ignores_none_candidates(self) -> None:
        self.assertFalse(matches_search_query("acme", None, "Other"))

    def test_matches_search_query_accepts_empty_query(self) -> None:
        self.assertTrue(matches_search_query("", None))


if __name__ == "__main__":
    unittest.main()
