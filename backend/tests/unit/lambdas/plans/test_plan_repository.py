from __future__ import annotations

import unittest

from lambdas.plans.infra.plan_repository import DynamoPlanRepository


class FakePlansTable:
    def __init__(self, items: list[dict]) -> None:
        self.items = items

    def query(self, **kwargs) -> dict:
        return {"Items": self.items}


class DynamoPlanRepositoryTests(unittest.TestCase):
    def test_get_by_slug_accepts_legacy_plan_without_entity_type(self) -> None:
        table = FakePlansTable(
            [
                {
                    "id": "legacy-free",
                    "slug": "free",
                    "name": "Gratis",
                    "created_at": "2026-06-07T03:08:23.715470+00:00",
                    "updated_at": "2026-06-07T03:08:23.715470+00:00",
                }
            ]
        )

        plan = DynamoPlanRepository(table).get_by_slug("free")

        self.assertEqual(plan.id, "legacy-free")
        self.assertEqual(plan.slug, "free")


if __name__ == "__main__":
    unittest.main()
