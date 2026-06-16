from __future__ import annotations

import unittest
from datetime import UTC, datetime

from lambdas.tenants.domain.commands import ToggleStatusCommand, UpdateTenantCommand
from lambdas.tenants.domain.enums import SriEnvironment, TenantStatus
from lambdas.tenants.domain.errors import (
    SubscriptionRenewalPaymentAlreadyAppliedError,
    SubscriptionRenewalPaymentNotConfirmedError,
    SubscriptionRenewalPlanMismatchError,
    TenantNotFoundError,
    TenantRucAlreadyExistsError,
)
from lambdas.tenants.domain.events import TenantCreatedEvent
from lambdas.tenants.domain.repositories.i_payment_reader import IPaymentReader, PaymentRecord
from lambdas.tenants.use_cases.apply_subscription_renewal import ApplySubscriptionRenewalUseCase
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


class FakePaymentReader(IPaymentReader):
    def __init__(self, *, payment: PaymentRecord | None = None) -> None:
        self._payment = payment
        self.marked: list[tuple[str, str]] = []

    def get_by_order_id(self, order_id: str) -> PaymentRecord:
        from lambdas.tenants.domain.errors import SubscriptionRenewalPaymentNotFoundError

        if self._payment is None or self._payment.order_id != order_id:
            raise SubscriptionRenewalPaymentNotFoundError()
        return self._payment

    def mark_applied_to_tenant(self, order_id: str, tenant_id: str) -> dict:
        self.marked.append((order_id, tenant_id))
        return {"ConditionCheck": {"TableName": "payments", "Key": {"id": f"PAYMENT#{order_id}"}}}


def _captured_payment(
    order_id: str = "ORD-1",
    plan_id: str = "uuid-basic",
    tenant_id: str = "",
    plan_cycle: str = "month",
) -> PaymentRecord:
    return PaymentRecord(
        order_id=order_id,
        tenant_id=tenant_id,
        plan_id=plan_id,
        amount="5.99",
        status="PAID",
        plan_cycle=plan_cycle,
        payer_id="PAY-1",
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

        updated, events = UpdateTenantUseCase(repo).execute(
            UpdateTenantCommand(
                tenant_id="tenant-1",
                updated_by="admin-1",
                trade_name="New Name",
                email="new@codelabs.com",
                sri_environment="production",
            )
        )

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

        updated, events = ToggleStatusUseCase(repo).execute(
            ToggleStatusCommand(
                tenant_id="tenant-1",
                new_status="suspended",
                updated_by="superadmin-1",
            )
        )

        self.assertEqual(updated.status, TenantStatus.SUSPENDED)
        self.assertEqual(events, [])

    def test_toggle_status_reactivates_inactive_tenant(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1", status=TenantStatus.INACTIVE)
        repo.tenants[tenant.id] = tenant

        updated, events = ToggleStatusUseCase(repo).execute(
            ToggleStatusCommand(
                tenant_id="tenant-1",
                new_status="active",
                updated_by="superadmin-1",
            )
        )

        self.assertEqual(updated.status, TenantStatus.ACTIVE)
        self.assertEqual(events, [])

    def test_toggle_status_rejects_inactive_to_suspended(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1", status=TenantStatus.INACTIVE)
        repo.tenants[tenant.id] = tenant

        with self.assertRaises(ValidationError):
            ToggleStatusUseCase(repo).execute(
                ToggleStatusCommand(
                    tenant_id="tenant-1",
                    new_status="suspended",
                    updated_by="superadmin-1",
                )
            )

    def test_toggle_status_rejects_invalid_state(self) -> None:
        repo = FakeTenantRepository()

        with self.assertRaises(ValidationError):
            ToggleStatusUseCase(repo).execute(
                ToggleStatusCommand(
                    tenant_id="tenant-1",
                    new_status="blocked",
                    updated_by="superadmin-1",
                )
            )

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

        tenants, next_token = ListTenantsUseCase(repo).execute(
            ListTenantsQuery(
                limit=10,
                next_token="cursor-0",
                status="active",
                q="codelabs",
                ruc="1792146739001",
                sri_environment="testing",
                plan_status="active",
                created_from="2026-06-01T00:00:00+00:00",
                created_to="2026-06-08T23:59:59.999999+00:00",
            )
        )

        self.assertEqual(tenants, [expected])
        self.assertEqual(next_token, "cursor-1")
        self.assertEqual(repo.list_calls[0]["q"], "codelabs")
        self.assertEqual(repo.list_calls[0]["ruc"], "1792146739001")
        self.assertEqual(repo.list_calls[0]["sri_environment"], "testing")
        self.assertEqual(repo.list_calls[0]["plan_status"], "active")


class ApplySubscriptionRenewalUseCaseTests(unittest.TestCase):
    def _repo_with_tenant(self, **overrides) -> FakeTenantRepository:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1", **overrides)
        repo.tenants[tenant.id] = tenant
        return repo

    def _execute(self, repo=None, payment=None):
        _repo = repo or self._repo_with_tenant()
        _payment = payment or _captured_payment()
        reader = FakePaymentReader(payment=_payment)
        return (
            ApplySubscriptionRenewalUseCase(_repo, reader).execute(
                "tenant-1", _payment.order_id, "user-1"
            ),
            reader,
        )

    def test_extends_cycle_and_returns_result(self) -> None:
        repo = self._repo_with_tenant()
        (tenant, result, _), _ = self._execute(repo=repo)
        self.assertIsNotNone(tenant.plan_cycle_ends_at)
        self.assertEqual(result.tenant_id, "tenant-1")
        self.assertEqual(result.subscription_status, "active")
        self.assertIsNotNone(result.plan_cycle_ends_at)

    def test_extends_by_year_for_year_cycle(self) -> None:
        base = datetime.now(UTC)
        repo = self._repo_with_tenant(plan_cycle_ends_at=base)
        payment = _captured_payment(plan_cycle="year")
        (tenant, _, _), _ = self._execute(repo=repo, payment=payment)
        delta = tenant.plan_cycle_ends_at - base
        self.assertGreater(delta.days, 364)

    def test_marks_payment_applied(self) -> None:
        (_, _, _), reader = self._execute()
        self.assertEqual(len(reader.marked), 1)
        self.assertEqual(reader.marked[0], ("ORD-1", "tenant-1"))

    def test_raises_if_tenant_not_found(self) -> None:
        with self.assertRaises(TenantNotFoundError):
            ApplySubscriptionRenewalUseCase(
                FakeTenantRepository(), FakePaymentReader(payment=_captured_payment())
            ).execute("missing", "ORD-1", "user-1")

    def test_raises_if_payment_not_captured(self) -> None:
        payment = PaymentRecord(
            order_id="ORD-1",
            tenant_id="",
            plan_id="uuid-basic",
            amount="5.99",
            status="CREATED",
            plan_cycle="month",
            payer_id="",
        )
        with self.assertRaises(SubscriptionRenewalPaymentNotConfirmedError):
            self._execute(payment=payment)

    def test_raises_if_payment_applied_to_other_tenant(self) -> None:
        payment = _captured_payment(tenant_id="other-tenant")
        with self.assertRaises(SubscriptionRenewalPaymentAlreadyAppliedError):
            self._execute(payment=payment)

    def test_allows_retry_for_same_tenant(self) -> None:
        payment = _captured_payment(tenant_id="tenant-1")
        (_, result, _), _ = self._execute(payment=payment)
        self.assertEqual(result.tenant_id, "tenant-1")

    def test_raises_if_plan_mismatch(self) -> None:
        payment = _captured_payment(plan_id="uuid-pro")
        with self.assertRaises(SubscriptionRenewalPlanMismatchError):
            self._execute(payment=payment)


if __name__ == "__main__":
    unittest.main()
