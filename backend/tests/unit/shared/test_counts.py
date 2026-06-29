from __future__ import annotations

import unittest

from shared.db.counts import paginated_count


class PaginatedCountTests(unittest.TestCase):
    def test_sums_counts_across_pages(self) -> None:
        calls: list[dict] = []
        responses = [
            {"Count": 3, "LastEvaluatedKey": {"pk": "page-2"}},
            {"Count": 4},
        ]

        def query(**kwargs):
            calls.append(kwargs)
            return responses.pop(0)

        total = paginated_count(query, Select="COUNT")

        self.assertEqual(total, 7)
        self.assertEqual(calls[0], {"Select": "COUNT"})
        self.assertEqual(calls[1], {"Select": "COUNT", "ExclusiveStartKey": {"pk": "page-2"}})

    def test_does_not_mutate_input_kwargs(self) -> None:
        kwargs = {"Select": "COUNT"}

        paginated_count(lambda **_: {"Count": 1}, **kwargs)

        self.assertEqual(kwargs, {"Select": "COUNT"})


if __name__ == "__main__":
    unittest.main()
