from __future__ import annotations

import unittest
from decimal import Decimal
from typing import Any

from lambdas.plans.domain.commands import CreatePlanCommand, TogglePlanCommand, UpdatePlanCommand
from lambdas.plans.domain.errors import PlanNotFoundError
from lambdas.plans.domain.plan import Plan
from lambdas.plans.use_cases.create_plan import CreatePlanUseCase
from lambdas.plans.use_cases.get_plan import GetPlanBySlugUseCase
from lambdas.plans.use_cases.list_plans import ListPlansQuery, ListPlansUseCase
from lambdas.plans.use_cases.toggle_plan import TogglePlanUseCase
from lambdas.plans.use_cases.update_plan import UpdatePlanUseCase
from shared.errors import ValidationError

# ── Fake ──────────────────────────────────────────────────────────────────────


class FakePlanRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Plan] = {}
        self._by_slug: dict[str, Plan] = {}
        self.commit_calls: list[dict[str, Any]] = []

    def get_by_id(self, plan_id: str) -> Plan:
        if plan_id not in self._by_id:
            raise PlanNotFoundError()
        return self._by_id[plan_id]

    def get_by_slug(self, slug: str) -> Plan:
        if slug not in self._by_slug:
            raise PlanNotFoundError()
        return self._by_slug[slug]

    def save(self, plan: Plan) -> None:
        self._by_id[plan.id] = plan
        self._by_slug[plan.slug] = plan

    def commit(self, **kwargs: Any) -> None:
        self.commit_calls.append(kwargs)
        self.save(kwargs["plan"])

    def list(
        self,
        *,
        status: str | None = None,
        slug: str | None = None,
        q: str | None = None,
        limit_cycle: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> list[Plan]:
        plans = list(self._by_id.values())
        if status:
            active = status == "active"
            plans = [p for p in plans if p.active == active]
        if slug:
            needle = slug.strip().lower()
            plans = [p for p in plans if p.slug.lower() == needle]
        if limit_cycle:
            plans = [p for p in plans if p.limit_cycle == limit_cycle]
        if created_from:
            plans = [p for p in plans if p.created_at.isoformat() >= created_from]
        if created_to:
            plans = [p for p in plans if p.created_at.isoformat() <= created_to]
        if q:
            needle = q.strip().lower()
            plans = [
                p
                for p in plans
                if needle in p.name.lower()
                or needle in p.description.lower()
                or needle in p.slug.lower()
            ]
        return plans


def _cmd(**overrides) -> CreatePlanCommand:
    base = dict(
        slug="basic",
        name="Basic",
        description="For freelancers",
        monthly_price=Decimal("5.99"),
        annual_price=Decimal("57.00"),
        document_limit=50,
        limit_cycle="month",
        max_locations=1,
        max_emission_points=2,
        max_users=2,
        includes_credit_notes=True,
        includes_withholdings=True,
        includes_delivery_notes=True,
        includes_api=False,
        order=1,
        created_by="admin-1",
    )
    base.update(overrides)
    return CreatePlanCommand(**base)


# ── CreatePlanUseCase ─────────────────────────────────────────────────────────


class CreatePlanUseCaseTests(unittest.TestCase):
    def test_creates_plan_with_uuid_as_pk(self) -> None:
        repo = FakePlanRepository()
        plan = CreatePlanUseCase(repo).execute(_cmd())
        self.assertEqual(plan.slug, "basic")
        self.assertEqual(len(plan.id), 36)  # UUID
        self.assertNotEqual(plan.id, plan.slug)  # PK != slug

    def test_create_does_not_persist_before_commit(self) -> None:
        repo = FakePlanRepository()
        plan = CreatePlanUseCase(repo).execute(_cmd())
        with self.assertRaises(PlanNotFoundError):
            repo.get_by_id(plan.id)
        self.assertEqual(repo.commit_calls, [])

    def test_slug_uniqueness_is_not_checked_by_use_case(self) -> None:
        # La unicidad del slug la garantiza el lock transaccional en el repositorio,
        # no el use case. Crear dos planes con el mismo slug en el use case no falla
        # aquí — el repositorio lanzaría PlanSlugExistsError al hacer commit().
        repo = FakePlanRepository()
        p1 = CreatePlanUseCase(repo).execute(_cmd())
        p2 = CreatePlanUseCase(repo).execute(_cmd())
        self.assertNotEqual(p1.id, p2.id)  # UUIDs distintos aunque slug igual

    def test_different_slug_creates_different_plan(self) -> None:
        repo = FakePlanRepository()
        p1 = CreatePlanUseCase(repo).execute(_cmd(slug="basic"))
        p2 = CreatePlanUseCase(repo).execute(_cmd(slug="pyme"))
        self.assertNotEqual(p1.id, p2.id)

    def test_fails_if_slug_has_uppercase(self) -> None:
        with self.assertRaises(ValidationError):
            CreatePlanUseCase(FakePlanRepository()).execute(_cmd(slug="Basic"))

    def test_fails_if_limit_cycle_invalid(self) -> None:
        with self.assertRaises(ValidationError):
            CreatePlanUseCase(FakePlanRepository()).execute(_cmd(limit_cycle="week"))

    def test_fails_if_price_negative(self) -> None:
        with self.assertRaises(ValidationError):
            CreatePlanUseCase(FakePlanRepository()).execute(_cmd(monthly_price=Decimal("-1.00")))

    def test_free_plan_year_cycle(self) -> None:
        repo = FakePlanRepository()
        plan = CreatePlanUseCase(repo).execute(
            _cmd(
                slug="free",
                monthly_price=Decimal("0.00"),
                annual_price=Decimal("0.00"),
                document_limit=20,
                limit_cycle="year",
                order=0,
            )
        )
        self.assertEqual(plan.limit_cycle, "year")

    def test_unlimited_limit_with_minus_one(self) -> None:
        repo = FakePlanRepository()
        plan = CreatePlanUseCase(repo).execute(
            _cmd(
                slug="enterprise",
                document_limit=-1,
                max_locations=-1,
                max_users=-1,
            )
        )
        self.assertEqual(plan.document_limit, -1)


# ── GetPlanBySlugUseCase ──────────────────────────────────────────────────────


class GetPlanBySlugUseCaseTests(unittest.TestCase):
    def test_returns_plan_by_slug(self) -> None:
        repo = FakePlanRepository()
        created = CreatePlanUseCase(repo).execute(_cmd())
        repo.save(created)
        found = GetPlanBySlugUseCase(repo).execute("basic")
        self.assertEqual(found.id, created.id)

    def test_fails_if_slug_not_found(self) -> None:
        with self.assertRaises(PlanNotFoundError):
            GetPlanBySlugUseCase(FakePlanRepository()).execute("missing")


# ── ListPlansUseCase ──────────────────────────────────────────────────────────


class ListPlansUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = FakePlanRepository()
        for slug, active, order in [("free", True, 0), ("basic", True, 1), ("inactive", False, 2)]:
            self.repo.save(Plan(slug=slug, name=slug, active=active, order=order))

    def test_filters_by_status_active(self) -> None:
        plans = ListPlansUseCase(self.repo).execute(ListPlansQuery(status="active"))
        self.assertEqual(len(plans), 2)
        self.assertNotIn("inactive", [p.slug for p in plans])

    def test_filters_by_status_inactive(self) -> None:
        plans = ListPlansUseCase(self.repo).execute(ListPlansQuery(status="inactive"))
        self.assertEqual([p.slug for p in plans], ["inactive"])

    def test_lists_all_when_status_omitted(self) -> None:
        self.assertEqual(len(ListPlansUseCase(self.repo).execute(ListPlansQuery())), 3)

    def test_sorted_by_order_field(self) -> None:
        plans = ListPlansUseCase(self.repo).execute(ListPlansQuery(status="active"))
        self.assertEqual(plans[0].slug, "free")
        self.assertEqual(plans[1].slug, "basic")


# ── UpdatePlanUseCase ─────────────────────────────────────────────────────────


class UpdatePlanUseCaseTests(unittest.TestCase):
    def _repo_with_plan(self) -> tuple[FakePlanRepository, Plan]:
        repo = FakePlanRepository()
        plan = CreatePlanUseCase(repo).execute(_cmd())
        repo.save(plan)
        return repo, plan

    def test_slug_as_id_does_not_find_plan(self) -> None:
        repo, _ = self._repo_with_plan()
        with self.assertRaises(PlanNotFoundError):
            UpdatePlanUseCase(repo).execute(
                UpdatePlanCommand(
                    id="basic",  # slug, not UUID → must not be found
                    updated_by="admin-1",
                    name="New Name",
                )
            )

    def test_updates_name_and_price_by_uuid(self) -> None:
        repo, plan = self._repo_with_plan()
        updated = UpdatePlanUseCase(repo).execute(
            UpdatePlanCommand(
                id=plan.id,
                updated_by="admin-1",
                name="Basic Plus",
                monthly_price=Decimal("6.99"),
            )
        )
        self.assertEqual(updated.name, "Basic Plus")
        self.assertEqual(updated.monthly_price, Decimal("6.99"))
        self.assertGreater(updated.version, 1)
        self.assertEqual(updated.slug, "basic")  # slug untouched

    def test_fails_if_uuid_not_found(self) -> None:
        with self.assertRaises(PlanNotFoundError):
            UpdatePlanUseCase(FakePlanRepository()).execute(
                UpdatePlanCommand(id="missing-uuid", updated_by="admin-1")
            )


# ── TogglePlanUseCase ─────────────────────────────────────────────────────────


class TogglePlanUseCaseTests(unittest.TestCase):
    def test_deactivates_by_uuid(self) -> None:
        repo = FakePlanRepository()
        plan = CreatePlanUseCase(repo).execute(_cmd())
        repo.save(plan)
        result = TogglePlanUseCase(repo).execute(
            TogglePlanCommand(id=plan.id, active=False, updated_by="admin-1")
        )
        self.assertFalse(result.active)
        self.assertFalse(repo.get_by_id(plan.id).active)

    def test_reactivates_by_uuid(self) -> None:
        repo = FakePlanRepository()
        plan = CreatePlanUseCase(repo).execute(_cmd())
        repo.save(plan)
        TogglePlanUseCase(repo).execute(
            TogglePlanCommand(id=plan.id, active=False, updated_by="admin-1")
        )
        result = TogglePlanUseCase(repo).execute(
            TogglePlanCommand(id=plan.id, active=True, updated_by="admin-1")
        )
        self.assertTrue(result.active)


if __name__ == "__main__":
    unittest.main()
