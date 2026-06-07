from __future__ import annotations

import unittest

from lambdas.tenants.domain.commands import ToggleStatusCommand, UpdateTenantCommand
from lambdas.tenants.domain.enums import SriEnvironment, TenantStatus
from lambdas.tenants.domain.errors import TenantRucAlreadyExistsError
from lambdas.tenants.domain.events import TenantCreatedEvent
from lambdas.tenants.use_cases.create_tenant import CreateTenantUseCase
from lambdas.tenants.use_cases.delete_tenant import DeleteTenantUseCase
from lambdas.tenants.use_cases.list_tenants import ListTenantsQuery, ListTenantsUseCase
from lambdas.tenants.use_cases.toggle_status import ToggleStatusUseCase
from lambdas.tenants.use_cases.update_tenant import UpdateTenantUseCase
from shared.errors import ValidationError
from tests.unit.support import (
    FakePlanCatalog,
    FakeTenantRepository,
    create_tenant_command,
    make_tenant,
)


class CreateTenantUseCaseTests(unittest.TestCase):
    def test_create_returns_tenant_and_event_without_persisting(self) -> None:
        repo = FakeTenantRepository()
        catalog = FakePlanCatalog()
        tenant, events = CreateTenantUseCase(repo, catalog).execute(create_tenant_command())

        self.assertEqual(tenant.ruc, create_tenant_command().ruc)
        self.assertEqual(tenant.email, "owner@codelabs.com")
        self.assertEqual(tenant.plan_id, "uuid-basic")
        self.assertEqual(catalog.checked_ids, ["uuid-basic"])
        self.assertEqual(repo.save_calls, [])
        self.assertEqual(repo.get_by_ruc_calls, [tenant.ruc])
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TenantCreatedEvent)
        self.assertEqual(events[0].tenant_id, tenant.id)

    def test_create_rejects_existing_ruc(self) -> None:
        repo = FakeTenantRepository()
        repo.existing_by_ruc = make_tenant()

        with self.assertRaises(TenantRucAlreadyExistsError):
            CreateTenantUseCase(repo, FakePlanCatalog()).execute(create_tenant_command())

    def test_create_rejects_invalid_plan_before_ruc_lookup(self) -> None:
        repo = FakeTenantRepository()

        with self.assertRaises(ValidationError):
            CreateTenantUseCase(repo, FakePlanCatalog(exists=False)).execute(
                create_tenant_command(plan_id="missing-plan")
            )

        self.assertEqual(repo.get_by_ruc_calls, [])


class TenantMutationUseCaseTests(unittest.TestCase):
    def test_update_changes_allowed_fields(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant

        updated, events = UpdateTenantUseCase(repo).execute(UpdateTenantCommand(
            tenant_id="tenant-1",
            updated_by="admin-1",
            trade_name="New Name",
            email="new@codelabs.com",
            sri_environment="production",
        ))

        self.assertEqual(updated.trade_name, "New Name")
        self.assertEqual(updated.email, "new@codelabs.com")
        self.assertEqual(updated.sri_environment, SriEnvironment.PRODUCTION)
        self.assertEqual(updated.updated_by, "admin-1")
        self.assertEqual(updated.version, 2)
        self.assertEqual(events, [])

    def test_toggle_status_validates_enum(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant

        updated, events = ToggleStatusUseCase(repo).execute(ToggleStatusCommand(
            tenant_id="tenant-1",
            new_status="suspended",
            updated_by="superadmin-1",
        ))

        self.assertEqual(updated.status, TenantStatus.SUSPENDED)
        self.assertEqual(events, [])

    def test_toggle_status_rejects_invalid_state(self) -> None:
        repo = FakeTenantRepository()

        with self.assertRaises(ValidationError):
            ToggleStatusUseCase(repo).execute(ToggleStatusCommand(
                tenant_id="tenant-1",
                new_status="blocked",
                updated_by="superadmin-1",
            ))

    def test_delete_soft_deletes(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant

        deleted, events = DeleteTenantUseCase(repo).execute("tenant-1", "superadmin-1")

        self.assertTrue(deleted.deleted)
        self.assertEqual(deleted.deleted_by, "superadmin-1")
        self.assertEqual(events, [])

    def test_list_delegates_query_to_repository(self) -> None:
        repo = FakeTenantRepository()
        expected = make_tenant(id="tenant-1")
        repo.list_result = ([expected], "cursor-1")

        tenants, next_token = ListTenantsUseCase(repo).execute(ListTenantsQuery(
            limit=10,
            next_token="cursor-0",
            status="active",
        ))

        self.assertEqual(tenants, [expected])
        self.assertEqual(next_token, "cursor-1")


if __name__ == "__main__":
    unittest.main()
