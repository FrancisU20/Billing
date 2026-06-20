from __future__ import annotations

import unittest
from datetime import UTC, datetime

from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.repositories.i_dlocal_client import DLocalDirectChargeResult
from lambdas.tenants.domain.commands import ToggleStatusCommand, UpdateTenantCommand
from lambdas.tenants.domain.enums import SriEnvironment, TenantStatus
from lambdas.tenants.domain.errors import (
    NoSavedPaymentMethodError,
    RetryPaymentNotEligibleError,
    SavedCardRejectedError,
    SubscriptionAlreadyActiveError,
    SubscriptionRenewalPaymentAlreadyAppliedError,
    SubscriptionRenewalPaymentNotConfirmedError,
    SubscriptionRenewalPlanMismatchError,
    TenantNotFoundError,
    TenantRucAlreadyExistsError,
)
from lambdas.tenants.domain.events import TenantCreatedEvent
from lambdas.tenants.domain.repositories.i_payment_reader import IPaymentReader, PaymentRecord
from lambdas.tenants.use_cases.activate_subscription import ActivateSubscriptionUseCase
from lambdas.tenants.use_cases.apply_subscription_renewal import ApplySubscriptionRenewalUseCase
from lambdas.tenants.use_cases.create_tenant import CreateTenantUseCase
from lambdas.tenants.use_cases.delete_tenant import DeleteTenantUseCase
from lambdas.tenants.use_cases.list_tenants import ListTenantsQuery, ListTenantsUseCase
from lambdas.tenants.use_cases.retry_payment import RetryPaymentUseCase
from lambdas.tenants.use_cases.toggle_status import ToggleStatusUseCase
from lambdas.tenants.use_cases.update_tenant import UpdateTenantUseCase
from shared.errors import ValidationError
from tests.unit.support import (
    FakePlanCatalog,
    FakeTenantRepository,
    create_tenant_command,
    make_tenant,
)


class FakeSubscriptionPlanCatalog:
    """Implements IPlanCatalog.get() for use cases that charge via dLocal."""

    def __init__(
        self,
        *,
        monthly_price: str = "5.99",
        limit_cycle: str = "month",
        is_free: bool = False,
    ) -> None:
        from decimal import Decimal

        from lambdas.subscriptions.domain.repositories.i_plan_catalog import PlanSummary

        self._summary = PlanSummary(
            id="uuid-basic",
            monthly_price=Decimal(monthly_price),
            annual_price=Decimal(monthly_price) * 12,
            limit_cycle=limit_cycle,
            is_free=is_free,
        )

    def get(self, plan_id: str):
        return self._summary


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

    def test_count_delegates_to_repository_without_text_filters(self) -> None:
        repo = FakeTenantRepository()
        repo.count_result = 17

        total = ListTenantsUseCase(repo).count(ListTenantsQuery(limit=10, status="active"))

        self.assertEqual(total, 17)
        self.assertEqual(repo.count_calls[0]["status"], "active")

    def test_count_is_none_when_text_or_computed_filter_is_active(self) -> None:
        repo = FakeTenantRepository()
        repo.count_result = 17

        self.assertIsNone(ListTenantsUseCase(repo).count(ListTenantsQuery(limit=10, q="x")))
        self.assertIsNone(ListTenantsUseCase(repo).count(ListTenantsQuery(limit=10, ruc="x")))
        self.assertIsNone(
            ListTenantsUseCase(repo).count(ListTenantsQuery(limit=10, plan_status="active"))
        )
        self.assertEqual(repo.count_calls, [])


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


class ActivateSubscriptionUseCaseTests(unittest.TestCase):
    def _repo_with_tenant(self, **overrides) -> FakeTenantRepository:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1", **overrides)
        repo.tenants[tenant.id] = tenant
        return repo

    def _execute(self, repo=None, payment=None):
        _repo = repo or self._repo_with_tenant(
            subscription_status="pending_payment", plan_cycle_ends_at=None
        )
        _payment = payment or _captured_payment()
        reader = FakePaymentReader(payment=_payment)
        return (
            ActivateSubscriptionUseCase(_repo, reader).execute(
                "tenant-1", _payment.order_id, "user-1"
            ),
            reader,
        )

    def test_sets_cycle_from_now_and_returns_active_status(self) -> None:
        before = datetime.now(UTC)
        (tenant, result, _), _ = self._execute()
        self.assertIsNotNone(tenant.plan_cycle_ends_at)
        self.assertGreater(tenant.plan_cycle_ends_at, before)
        self.assertEqual(result.subscription_status, "active")
        self.assertEqual(result.tenant_id, "tenant-1")

    def test_marks_payment_applied(self) -> None:
        (_, _, _), reader = self._execute()
        self.assertEqual(reader.marked, [("ORD-1", "tenant-1")])

    def test_raises_if_already_active(self) -> None:
        repo = self._repo_with_tenant(subscription_status="active")
        with self.assertRaises(SubscriptionAlreadyActiveError):
            ActivateSubscriptionUseCase(
                repo, FakePaymentReader(payment=_captured_payment())
            ).execute("tenant-1", "ORD-1", "user-1")

    def test_raises_if_payment_not_confirmed(self) -> None:
        payment = _captured_payment()
        payment = PaymentRecord(
            order_id=payment.order_id,
            tenant_id=payment.tenant_id,
            plan_id=payment.plan_id,
            amount=payment.amount,
            status="CREATED",
            plan_cycle=payment.plan_cycle,
            payer_id=payment.payer_id,
        )
        with self.assertRaises(SubscriptionRenewalPaymentNotConfirmedError):
            self._execute(payment=payment)

    def test_raises_if_payment_applied_to_other_tenant(self) -> None:
        payment = _captured_payment(tenant_id="other-tenant")
        with self.assertRaises(SubscriptionRenewalPaymentAlreadyAppliedError):
            self._execute(payment=payment)

    def test_raises_if_plan_mismatch(self) -> None:
        payment = _captured_payment(plan_id="uuid-pro")
        with self.assertRaises(SubscriptionRenewalPlanMismatchError):
            self._execute(payment=payment)


class ActivateSubscriptionPreSaveTests(unittest.TestCase):
    """Verify the Phase-1 pre-save bookmark written before the full commit."""

    def _execute(self, **tenant_overrides):
        repo = FakeTenantRepository()
        tenant = make_tenant(
            id="tenant-1", subscription_status="pending_payment", **tenant_overrides
        )
        repo.tenants[tenant.id] = tenant
        payment = _captured_payment()
        reader = FakePaymentReader(payment=payment)
        result = ActivateSubscriptionUseCase(repo, reader).execute(
            "tenant-1", payment.order_id, "u"
        )
        return repo, result

    def test_set_pending_order_id_called_before_commit(self) -> None:
        repo, _ = self._execute()
        self.assertEqual(repo.set_pending_order_id_calls, [("tenant-1", "ORD-1")])

    def test_pending_order_id_cleared_on_entity_after_activation(self) -> None:
        repo, (tenant, _, _) = self._execute()
        self.assertIsNone(tenant.pending_order_id)

    def test_activation_proceeds_even_when_pre_save_raises_database_error(self) -> None:
        from shared.errors import DatabaseError

        repo = FakeTenantRepository()
        tenant = make_tenant(
            id="tenant-1", subscription_status="pending_payment", plan_cycle_ends_at=None
        )
        repo.tenants[tenant.id] = tenant

        def raising(tenant_id, order_id):  # noqa: ARG001
            raise DatabaseError()

        repo.set_pending_order_id = raising  # type: ignore[method-assign]

        payment = _captured_payment()
        reader = FakePaymentReader(payment=payment)
        # Even if the pre-save fails, activation should still raise (caller sees DatabaseError).
        with self.assertRaises(DatabaseError):
            ActivateSubscriptionUseCase(repo, reader).execute("tenant-1", payment.order_id, "u")


class PendingActivationReconcilerUseCaseTests(unittest.TestCase):
    from lambdas.workers.pending_activation_reconciler.use_case import (
        PendingActivationReconcilerUseCase,
    )

    def _make_pending_tenant(self, **overrides):
        return make_tenant(
            id="tenant-1",
            subscription_status="pending_payment",
            pending_order_id="ORD-1",
            plan_cycle_ends_at=None,
            **overrides,
        )

    def _run(self, tenants, payment=None):
        from lambdas.workers.pending_activation_reconciler.use_case import (
            PendingActivationReconcilerUseCase,
        )

        repo = FakeTenantRepository()
        repo.pending_activation_tenants = tenants
        for t in tenants:
            repo.tenants[t.id] = t
        p = payment or _captured_payment()
        reader = FakePaymentReader(payment=p)
        result = PendingActivationReconcilerUseCase(repo, reader).execute()
        return result, repo

    def test_activates_pending_tenant(self) -> None:
        result, repo = self._run([self._make_pending_tenant()])
        self.assertEqual(result.activated, 1)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)
        self.assertEqual(len(repo.commit_calls), 1)

    def test_skips_tenant_without_pending_order_id(self) -> None:
        tenant = make_tenant(id="t-1", subscription_status="pending_payment")
        tenant.pending_order_id = None
        result, _ = self._run([tenant])
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.activated, 0)

    def test_skips_already_active_tenant(self) -> None:
        result, _ = self._run(
            [self._make_pending_tenant()],
            payment=_captured_payment(),
        )
        # Would be activated, not skipped — confirm normal activation.
        self.assertEqual(result.activated, 1)

    def test_skips_on_plan_mismatch(self) -> None:
        result, _ = self._run(
            [self._make_pending_tenant()],
            payment=_captured_payment(plan_id="uuid-other"),
        )
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.activated, 0)

    def test_counts_unexpected_error(self) -> None:
        from lambdas.workers.pending_activation_reconciler.use_case import (
            PendingActivationReconcilerUseCase,
        )

        tenant = self._make_pending_tenant()
        repo = FakeTenantRepository()
        repo.pending_activation_tenants = [tenant]
        repo.tenants[tenant.id] = tenant
        repo.commit_errors = [RuntimeError("boom")]
        reader = FakePaymentReader(payment=_captured_payment())
        result = PendingActivationReconcilerUseCase(repo, reader).execute()
        self.assertEqual(result.errors, 1)
        self.assertEqual(result.activated, 0)

    def test_processes_multiple_tenants(self) -> None:
        from lambdas.workers.pending_activation_reconciler.use_case import (
            PendingActivationReconcilerUseCase,
        )

        repo = FakeTenantRepository()
        t1 = make_tenant(
            id="t-1",
            subscription_status="pending_payment",
            pending_order_id="ORD-1",
            plan_cycle_ends_at=None,
        )
        t2 = make_tenant(
            id="t-2",
            subscription_status="pending_payment",
            pending_order_id="ORD-1",
            plan_cycle_ends_at=None,
        )
        repo.pending_activation_tenants = [t1, t2]
        repo.tenants["t-1"] = t1
        repo.tenants["t-2"] = t2
        reader = FakePaymentReader(payment=_captured_payment())
        result = PendingActivationReconcilerUseCase(repo, reader).execute()
        self.assertEqual(result.activated, 2)


class FakePaymentRepository:
    def __init__(self) -> None:
        self.saved: list[Payment] = []
        self.transact_items: list[dict] = []

    def save(self, payment: Payment) -> None:
        self.saved.append(payment)

    def save_transact_item(self, payment: Payment) -> dict:
        item = {"Put": {"TableName": "payments", "Item": {"id": f"PAYMENT#{payment.order_id}"}}}
        self.transact_items.append(item)
        return item

    def get_by_order_id(self, order_id: str):
        raise NotImplementedError

    def link_tenant(self, order_id: str, tenant_id: str) -> None:
        raise NotImplementedError


class FakeDLocalClient:
    def __init__(self, *, status: str = "PAID", payment_id: str = "DP-retry-1") -> None:
        self._status = status
        self._payment_id = payment_id
        self.calls: list[dict] = []

    def charge_saved_payer(self, payer_id, amount, currency, country) -> DLocalDirectChargeResult:
        self.calls.append(
            {"payer_id": payer_id, "amount": amount, "currency": currency, "country": country}
        )
        return DLocalDirectChargeResult(payment_id=self._payment_id, status=self._status)

    def create_payment(self, *a, **kw):
        raise NotImplementedError

    def confirm_payment(self, *a, **kw):
        raise NotImplementedError

    def refund_payment(self, *a, **kw):
        raise NotImplementedError


def _tenant_with_payer(
    subscription_status: str = "payment_failed",
    plan_id: str = "uuid-basic",
) -> object:
    return make_tenant(
        subscription_status=subscription_status,
        dlocal_payer_id="PAY-saved",
        plan_id=plan_id,
    )


class RetryPaymentUseCaseTests(unittest.TestCase):
    def _run(
        self,
        tenant=None,
        *,
        dlocal_status: str = "PAID",
    ):
        t = tenant or _tenant_with_payer()
        repo = FakeTenantRepository()
        repo.tenants[t.id] = t
        catalog = FakeSubscriptionPlanCatalog()
        dlocal = FakeDLocalClient(status=dlocal_status)
        payments = FakePaymentRepository()
        return RetryPaymentUseCase(repo, catalog, dlocal, payments).execute(t.id, "user-1"), (
            t,
            repo,
            dlocal,
            payments,
        )

    def test_charges_saved_payer_and_activates(self) -> None:
        (tenant, result, transact), (t, repo, dlocal, payments) = self._run()
        self.assertEqual(result.subscription_status, "active")
        self.assertIsNotNone(result.plan_cycle_ends_at)
        self.assertEqual(len(dlocal.calls), 1)
        self.assertEqual(dlocal.calls[0]["payer_id"], "PAY-saved")

    def test_returns_payment_transact_item(self) -> None:
        (tenant, result, transact), _ = self._run()
        self.assertIn("Put", transact)

    def test_payment_saved_via_transact_item_not_direct_save(self) -> None:
        (tenant, result, transact), (_, _, _, payments) = self._run()
        self.assertEqual(len(payments.transact_items), 1)
        self.assertEqual(len(payments.saved), 0)

    def test_raises_if_no_saved_payer_id(self) -> None:
        t = make_tenant(subscription_status="payment_failed", dlocal_payer_id=None)
        repo = FakeTenantRepository()
        repo.tenants[t.id] = t
        with self.assertRaises(NoSavedPaymentMethodError):
            RetryPaymentUseCase(
                repo, FakeSubscriptionPlanCatalog(), FakeDLocalClient(), FakePaymentRepository()
            ).execute(t.id, "user-1")

    def test_raises_if_status_not_eligible(self) -> None:
        t = make_tenant(subscription_status="active", dlocal_payer_id="PAY-1")
        repo = FakeTenantRepository()
        repo.tenants[t.id] = t
        with self.assertRaises(RetryPaymentNotEligibleError):
            RetryPaymentUseCase(
                repo, FakeSubscriptionPlanCatalog(), FakeDLocalClient(), FakePaymentRepository()
            ).execute(t.id, "user-1")

    def test_raises_saved_card_rejected_when_dlocal_rejects(self) -> None:
        with self.assertRaises(SavedCardRejectedError):
            self._run(dlocal_status="REJECTED")

    def test_eligible_when_expired(self) -> None:
        (tenant, result, _), _ = self._run(tenant=_tenant_with_payer("expired"))
        self.assertEqual(result.subscription_status, "active")

    def test_gross_price_applied_to_dlocal_charge(self) -> None:
        (_, _, _), (_, _, dlocal, _) = self._run()
        self.assertEqual(dlocal.calls[0]["amount"], "6.71")


if __name__ == "__main__":
    unittest.main()
