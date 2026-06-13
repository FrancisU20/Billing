from __future__ import annotations

import unittest

from lambdas.onboarding.domain.commands import RegisterTenantCommand
from lambdas.onboarding.domain.errors import PlanNotActiveError, PlanNotFoundError
from lambdas.onboarding.domain.events import EnterpriseLeadCreatedEvent
from lambdas.onboarding.domain.repositories.i_plan_catalog import IPlanCatalog, PlanSummary
from lambdas.onboarding.use_cases.register_tenant_use_case import RegisterTenantUseCase
from lambdas.tenants.domain.errors import TenantRucAlreadyExistsError
from lambdas.tenants.domain.events import TenantCreatedEvent
from tests.unit.support import FakeTenantRepository, make_tenant, tenant_payload


class FakeOnboardingPlanCatalog(IPlanCatalog):
    def __init__(
        self,
        *,
        exists: bool = True,
        active: bool = True,
        self_service: bool = True,
        limit_cycle: str = "month",
    ) -> None:
        self.exists = exists
        self.active = active
        self.self_service = self_service
        self.limit_cycle = limit_cycle
        self.checked_ids: list[str] = []

    def get(self, plan_id: str) -> PlanSummary:
        self.checked_ids.append(plan_id)
        if not self.exists:
            raise PlanNotFoundError()
        if not self.active:
            raise PlanNotActiveError()
        return PlanSummary(id=plan_id, self_service=self.self_service, limit_cycle=self.limit_cycle)


def register_command(**overrides) -> RegisterTenantCommand:
    payload = tenant_payload()
    payload.pop("created_by", None)
    payload.update(overrides)
    return RegisterTenantCommand(**payload)


class RegisterTenantUseCaseTests(unittest.TestCase):
    def test_self_service_plan_creates_tenant(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(self_service=True)

        result = RegisterTenantUseCase(catalog, repo).execute(register_command())

        self.assertIsNotNone(result.tenant)
        self.assertIsNone(result.lead)
        self.assertEqual(result.tenant.ruc, register_command().ruc)
        self.assertEqual(catalog.checked_ids, ["uuid-basic"])
        self.assertEqual(repo.get_by_ruc_calls, [result.tenant.ruc])
        self.assertEqual(len(result.events), 1)
        self.assertIsInstance(result.events[0], TenantCreatedEvent)
        self.assertEqual(result.events[0].tenant_id, result.tenant.id)

    def test_self_service_plan_rejects_existing_ruc(self) -> None:
        repo = FakeTenantRepository()
        repo.existing_by_ruc = make_tenant()
        catalog = FakeOnboardingPlanCatalog(self_service=True)

        with self.assertRaises(TenantRucAlreadyExistsError):
            RegisterTenantUseCase(catalog, repo).execute(register_command())

    def test_non_self_service_plan_creates_enterprise_lead(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(self_service=False)

        result = RegisterTenantUseCase(catalog, repo).execute(register_command())

        self.assertIsNone(result.tenant)
        self.assertIsNotNone(result.lead)
        self.assertEqual(result.lead.ruc, register_command().ruc)
        self.assertEqual(result.lead.plan_id, "uuid-basic")
        self.assertEqual(repo.get_by_ruc_calls, [])
        self.assertEqual(len(result.events), 1)
        self.assertIsInstance(result.events[0], EnterpriseLeadCreatedEvent)
        self.assertEqual(result.events[0].lead_id, result.lead.id)

    def test_unknown_plan_raises_not_found(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(exists=False)

        with self.assertRaises(PlanNotFoundError):
            RegisterTenantUseCase(catalog, repo).execute(register_command())

        self.assertEqual(repo.get_by_ruc_calls, [])

    def test_inactive_plan_raises_not_active(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakeOnboardingPlanCatalog(active=False)

        with self.assertRaises(PlanNotActiveError):
            RegisterTenantUseCase(catalog, repo).execute(register_command())

        self.assertEqual(repo.get_by_ruc_calls, [])


if __name__ == "__main__":
    unittest.main()
