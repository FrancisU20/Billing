from __future__ import annotations

import unittest

from lambdas.tenants.domain.commands import ToggleStatusCommand, UpdateTenantCommand
from lambdas.tenants.domain.enums import AmbienteSri, EstadoTenant
from lambdas.tenants.domain.errors import TenantRucAlreadyExistsError
from lambdas.tenants.domain.events import (
    TenantCreatedEvent,
    TenantDeletedEvent,
    TenantStatusChangedEvent,
    TenantUpdatedEvent,
)
from lambdas.tenants.use_cases.create_tenant import CreateTenantUseCase
from lambdas.tenants.use_cases.delete_tenant import DeleteTenantUseCase
from lambdas.tenants.use_cases.list_tenants import ListTenantsQuery, ListTenantsUseCase
from lambdas.tenants.use_cases.toggle_status import ToggleStatusUseCase
from lambdas.tenants.use_cases.update_tenant import UpdateTenantUseCase
from shared.errors import ValidationError
from tests.unit.support import (
    FakeTenantRepository,
    create_tenant_command,
    make_tenant,
)


class CreateTenantUseCaseTests(unittest.TestCase):
    def test_create_returns_tenant_and_event_without_persisting(self) -> None:
        repo = FakeTenantRepository()
        tenant, events = CreateTenantUseCase(repo).execute(create_tenant_command())

        self.assertEqual(tenant.ruc, create_tenant_command().ruc)
        self.assertEqual(tenant.email, "owner@codelabs.com")
        self.assertEqual(repo.save_calls, [])
        self.assertEqual(repo.get_by_ruc_calls, [tenant.ruc])
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TenantCreatedEvent)
        self.assertEqual(events[0].tenant_id, tenant.id)

    def test_create_rejects_existing_ruc(self) -> None:
        repo = FakeTenantRepository()
        repo.existing_by_ruc = make_tenant()

        with self.assertRaises(TenantRucAlreadyExistsError):
            CreateTenantUseCase(repo).execute(create_tenant_command())


class TenantMutationUseCaseTests(unittest.TestCase):
    def test_update_changes_allowed_fields_and_emits_event(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant

        updated, events = UpdateTenantUseCase(repo).execute(UpdateTenantCommand(
            tenant_id="tenant-1",
            updated_by="admin-1",
            nombre_comercial="Nuevo Nombre",
            email="nuevo@codelabs.com",
            ambiente_sri="produccion",
        ))

        self.assertEqual(updated.nombre_comercial, "Nuevo Nombre")
        self.assertEqual(updated.email, "nuevo@codelabs.com")
        self.assertEqual(updated.ambiente_sri, AmbienteSri.PRODUCCION)
        self.assertEqual(updated.updated_by, "admin-1")
        self.assertEqual(updated.version, 2)
        self.assertIsInstance(events[0], TenantUpdatedEvent)

    def test_toggle_status_validates_enum_and_emits_event(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant

        updated, events = ToggleStatusUseCase(repo).execute(ToggleStatusCommand(
            tenant_id="tenant-1",
            nuevo_estado="suspendido",
            updated_by="superadmin-1",
        ))

        self.assertEqual(updated.estado, EstadoTenant.SUSPENDIDO)
        self.assertIsInstance(events[0], TenantStatusChangedEvent)
        self.assertEqual(events[0].nuevo_estado, "suspendido")

    def test_toggle_status_rejects_invalid_state(self) -> None:
        repo = FakeTenantRepository()

        with self.assertRaises(ValidationError):
            ToggleStatusUseCase(repo).execute(ToggleStatusCommand(
                tenant_id="tenant-1",
                nuevo_estado="bloqueado",
                updated_by="superadmin-1",
            ))

    def test_delete_soft_deletes_and_emits_event(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant

        deleted, events = DeleteTenantUseCase(repo).execute("tenant-1", "superadmin-1")

        self.assertTrue(deleted.deleted)
        self.assertEqual(deleted.deleted_by, "superadmin-1")
        self.assertIsInstance(events[0], TenantDeletedEvent)

    def test_list_delegates_query_to_repository(self) -> None:
        repo = FakeTenantRepository()
        expected = make_tenant(id="tenant-1")
        repo.list_result = ([expected], "cursor-1")

        tenants, next_token = ListTenantsUseCase(repo).execute(ListTenantsQuery(
            limit=10,
            next_token="cursor-0",
            estado="activo",
        ))

        self.assertEqual(tenants, [expected])
        self.assertEqual(next_token, "cursor-1")


if __name__ == "__main__":
    unittest.main()
