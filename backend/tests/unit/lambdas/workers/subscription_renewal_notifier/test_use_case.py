from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.repositories.i_dlocal_client import DLocalDirectChargeResult
from lambdas.workers.email_notifications.ports import EmailSender
from lambdas.workers.subscription_renewal_notifier.use_case import (
    _PAYMENT_FAILED_GRACE_DAYS,
    NotifySubscriptionRenewalUseCase,
)
from shared.errors import OptimisticLockError
from tests.unit.support import FakeTenantRepository, make_tenant


class FakeEmailSender(EmailSender):
    def __init__(self) -> None:
        self.reminders_sent: list[dict] = []
        self.expirations_sent: list[dict] = []
        self.payment_failed_sent: list[dict] = []
        self.reconciliation_alerts_sent: list[dict] = []

    def send_onboarding_otp(self, *, email, legal_rep_name, otp, expires_at):
        raise NotImplementedError

    def send_welcome(self, *, email, legal_rep_name, temp_password):
        raise NotImplementedError

    def send_password_reset(self, *, email, code, expires_at):
        raise NotImplementedError

    def send_enterprise_lead_notification(
        self, *, superadmin_email, trade_name, ruc, email, plan_id, plan_name=""
    ):
        raise NotImplementedError

    def send_certificate_expiry_alert(
        self, *, email, legal_rep_name, trade_name, ruc, cert_expires_at, days_remaining
    ):
        raise NotImplementedError

    def send_subscription_renewal_reminder(
        self, *, email, legal_rep_name, trade_name, plan_cycle_ends_at, days_remaining, renewal_url
    ):
        self.reminders_sent.append(
            {
                "email": email,
                "trade_name": trade_name,
                "plan_cycle_ends_at": plan_cycle_ends_at,
                "days_remaining": days_remaining,
                "renewal_url": renewal_url,
            }
        )

    def send_subscription_expired(self, *, email, legal_rep_name, trade_name, renewal_url):
        self.expirations_sent.append(
            {"email": email, "trade_name": trade_name, "renewal_url": renewal_url}
        )

    def send_payment_failed(self, *, email, legal_rep_name, trade_name, renewal_url):
        self.payment_failed_sent.append(
            {"email": email, "trade_name": trade_name, "renewal_url": renewal_url}
        )

    def send_document_authorized(
        self, *, email, legal_rep_name, document_id, access_key, authorization_number
    ):
        raise NotImplementedError

    def send_document_rejected(self, *, email, legal_rep_name, document_id, access_key, sri_errors):
        raise NotImplementedError

    def send_document_failed_permanent(self, *, email, legal_rep_name, document_id, access_key):
        raise NotImplementedError

    def send_document_to_buyer(
        self,
        *,
        email,
        buyer_name,
        document_id,
        access_key,
        authorization_number,
        xml_content,
        xml_filename,
        ride_content,
        ride_filename,
    ):
        raise NotImplementedError

    def send_orphan_payment_alert(
        self, *, superadmin_email, order_id, payer_email, plan_id, amount, currency, confirmed_at
    ):
        raise NotImplementedError

    def send_auto_renewal_reconciliation_alert(
        self,
        *,
        billing_email,
        tenant_id,
        tenant_email,
        trade_name,
        order_id,
        plan_id,
        amount,
        currency,
        confirmed_at,
        reason,
    ):
        self.reconciliation_alerts_sent.append(
            {
                "billing_email": billing_email,
                "tenant_id": tenant_id,
                "tenant_email": tenant_email,
                "trade_name": trade_name,
                "order_id": order_id,
                "plan_id": plan_id,
                "amount": amount,
                "currency": currency,
                "confirmed_at": confirmed_at,
                "reason": reason,
            }
        )


_NOW = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)


def _repo_with(*tenants) -> FakeTenantRepository:
    repo = FakeTenantRepository()
    repo.subscription_expiry_due = list(tenants)
    return repo


def _tenant_expiring_in(days: int, *, reminder_sent: bool = False, **kwargs):
    ends_at = _NOW + timedelta(days=days)
    tenant = make_tenant(
        plan_cycle_ends_at=ends_at,
        subscription_status="active",
        **kwargs,
    )
    if reminder_sent:
        tenant.subscription_renewal_reminder_sent_at = _NOW - timedelta(days=1)
    return tenant


class NotifySubscriptionRenewalUseCaseTests(unittest.TestCase):
    def _run(self, repo, email_sender=None):
        sender = email_sender or FakeEmailSender()
        result = NotifySubscriptionRenewalUseCase(
            repo, sender, now=_NOW, frontend_url="https://billing.example.com"
        ).execute()
        return result, sender

    def test_sends_reminder_for_tenant_expiring_within_7_days(self) -> None:
        tenant = _tenant_expiring_in(5)
        repo = _repo_with(tenant)
        result, sender = self._run(repo)

        self.assertEqual(result.reminders_sent, 1)
        self.assertEqual(result.expirations_processed, 0)
        self.assertEqual(len(sender.reminders_sent), 1)
        self.assertEqual(sender.reminders_sent[0]["days_remaining"], 5)

    def test_marks_reminder_sent_at_on_tenant(self) -> None:
        tenant = _tenant_expiring_in(3)
        repo = _repo_with(tenant)
        self._run(repo)

        self.assertIsNotNone(tenant.subscription_renewal_reminder_sent_at)
        self.assertEqual(len(repo.save_calls), 1)

    def test_does_not_send_duplicate_reminder(self) -> None:
        tenant = _tenant_expiring_in(5, reminder_sent=True)
        repo = _repo_with(tenant)
        result, sender = self._run(repo)

        self.assertEqual(result.reminders_sent, 0)
        self.assertEqual(len(sender.reminders_sent), 0)
        self.assertEqual(len(repo.save_calls), 0)

    def test_expires_subscription_for_past_due_tenant(self) -> None:
        tenant = _tenant_expiring_in(-1)
        repo = _repo_with(tenant)
        result, sender = self._run(repo)

        self.assertEqual(result.expirations_processed, 1)
        self.assertEqual(result.reminders_sent, 0)
        self.assertEqual(len(sender.expirations_sent), 1)
        self.assertEqual(tenant.subscription_status, "expired")

    def test_saves_tenant_after_expiry(self) -> None:
        tenant = _tenant_expiring_in(-1)
        repo = _repo_with(tenant)
        self._run(repo)
        self.assertEqual(len(repo.save_calls), 1)

    def test_skips_tenant_with_none_plan_cycle_ends_at(self) -> None:
        tenant = make_tenant(plan_cycle_ends_at=None)
        repo = _repo_with(tenant)
        result, sender = self._run(repo)

        self.assertEqual(result.reminders_sent, 0)
        self.assertEqual(result.expirations_processed, 0)
        self.assertEqual(len(repo.save_calls), 0)

    def test_continues_processing_on_optimistic_lock_error(self) -> None:
        tenant_a = _tenant_expiring_in(-1)
        tenant_b = _tenant_expiring_in(3)
        repo = _repo_with(tenant_a, tenant_b)
        repo.save_errors[tenant_a.id] = OptimisticLockError()

        result, sender = self._run(repo)

        # tenant_a failed with lock error → skipped; tenant_b processed normally
        self.assertEqual(result.reminders_sent, 1)
        self.assertEqual(result.expirations_processed, 0)

    def test_processes_multiple_tenants(self) -> None:
        tenants = [_tenant_expiring_in(-2), _tenant_expiring_in(4), _tenant_expiring_in(6)]
        repo = _repo_with(*tenants)
        result, _ = self._run(repo)

        self.assertEqual(result.expirations_processed, 1)
        self.assertEqual(result.reminders_sent, 2)


class FakeLocalPlanCatalog:
    def __init__(self, *, monthly_price: Decimal = Decimal("5.99")) -> None:
        self._price = monthly_price

    def get(self, plan_id: str):
        from lambdas.subscriptions.domain.repositories.i_plan_catalog import PlanSummary

        return PlanSummary(
            id=plan_id,
            monthly_price=self._price,
            annual_price=self._price * 12,
            limit_cycle="month",
            is_free=False,
        )


class FakeDLocalClient:
    def __init__(
        self,
        *,
        status: str = "PAID",
        payment_id: str = "DP-auto-1",
        raises: Exception | None = None,
    ) -> None:
        self._status = status
        self._payment_id = payment_id
        self._raises = raises
        self.calls: int = 0

    def charge_saved_payer(self, payer_id, amount, currency, country) -> DLocalDirectChargeResult:
        self.calls += 1
        if self._raises:
            raise self._raises
        return DLocalDirectChargeResult(payment_id=self._payment_id, status=self._status)

    def create_payment(self, *a, **kw):
        raise NotImplementedError

    def confirm_payment(self, *a, **kw):
        raise NotImplementedError

    def refund_payment(self, *a, **kw):
        raise NotImplementedError


class FakePaymentRepository:
    def __init__(self) -> None:
        self.saved: list[Payment] = []
        self.transact_payments: list[Payment] = []
        self.transact_items: list[dict] = []
        self.reconciliation_markers: dict[tuple[str, datetime], dict] = {}
        self.deleted_reconciliation_markers: list[tuple[str, datetime]] = []

    def save(self, payment: Payment) -> None:
        self.saved.append(payment)

    def save_transact_item(self, payment: Payment) -> dict:
        item = {"Put": {"TableName": "payments", "Item": {"id": f"PAYMENT#{payment.order_id}"}}}
        self.transact_payments.append(payment)
        self.transact_items.append(item)
        return item

    def get_by_order_id(self, order_id: str):
        raise NotImplementedError

    def link_tenant(self, order_id: str, tenant_id: str) -> None:
        raise NotImplementedError

    def create_auto_renewal_reconciliation_marker(
        self, *, tenant_id, cycle_ends_at, plan_id, amount, currency, reason
    ) -> bool:
        key = (tenant_id, cycle_ends_at)
        if key in self.reconciliation_markers:
            return False
        self.reconciliation_markers[key] = {
            "plan_id": plan_id,
            "amount": amount,
            "currency": currency,
            "reason": reason,
        }
        return True

    def save_auto_renewal_reconciliation_marker(
        self, payment, *, tenant_id, cycle_ends_at, reason
    ) -> None:
        self.reconciliation_markers[(tenant_id, cycle_ends_at)] = {
            "payment": payment,
            "reason": reason,
        }

    def delete_auto_renewal_reconciliation_marker(self, *, tenant_id, cycle_ends_at) -> None:
        self.deleted_reconciliation_markers.append((tenant_id, cycle_ends_at))
        self.reconciliation_markers.pop((tenant_id, cycle_ends_at), None)


def _auto_charge_deps(*, dlocal_status: str = "PAID", dlocal_raises: Exception | None = None):
    catalog = FakeLocalPlanCatalog(monthly_price=Decimal("5.99"))
    dlocal = FakeDLocalClient(status=dlocal_status, raises=dlocal_raises)
    payments = FakePaymentRepository()
    return catalog, dlocal, payments


def _run_with_auto_charge(
    repo,
    *,
    dlocal_status: str = "PAID",
    dlocal_raises: Exception | None = None,
    sender=None,
):
    catalog, dlocal, payments = _auto_charge_deps(
        dlocal_status=dlocal_status,
        dlocal_raises=dlocal_raises,
    )
    email_sender = sender or FakeEmailSender()
    result = NotifySubscriptionRenewalUseCase(
        repo,
        email_sender,
        now=_NOW,
        frontend_url="https://billing.example.com",
        plan_catalog=catalog,
        dlocal=dlocal,
        payment_repo=payments,
        reconciliation_notifier=email_sender,
        reconciliation_email="billing@example.com",
    ).execute()
    return result, email_sender, dlocal, payments


class AutoChargeTests(unittest.TestCase):
    def test_auto_charges_expired_tenant_with_saved_card(self) -> None:
        tenant = make_tenant(
            subscription_status="active",
            plan_cycle_ends_at=_NOW - timedelta(days=1),
            dlocal_payer_id="PAY-1",
        )
        repo = _repo_with(tenant)
        original_cycle_ends_at = tenant.plan_cycle_ends_at
        result, _, dlocal, payments = _run_with_auto_charge(repo)

        self.assertEqual(result.auto_charged, 1)
        self.assertEqual(result.expirations_processed, 0)
        self.assertEqual(dlocal.calls, 1)
        self.assertEqual(payments.saved, [])
        self.assertEqual(len(payments.transact_payments), 1)
        self.assertEqual(len(repo.save_calls), 0)
        self.assertEqual(len(repo.commit_calls), 1)
        self.assertEqual(repo.commit_calls[0]["action"], "SUBSCRIPTION_AUTO_RENEWAL")
        self.assertEqual(repo.commit_calls[0]["extra_transact_items"], payments.transact_items)
        self.assertEqual(payments.reconciliation_markers, {})
        self.assertEqual(
            payments.deleted_reconciliation_markers,
            [(tenant.id, original_cycle_ends_at)],
        )
        self.assertEqual(tenant.subscription_status, "active")

    def test_expires_when_no_saved_card(self) -> None:
        tenant = make_tenant(
            subscription_status="active",
            plan_cycle_ends_at=_NOW - timedelta(days=1),
            dlocal_payer_id=None,
        )
        repo = _repo_with(tenant)
        result, sender, _, _ = _run_with_auto_charge(repo)

        self.assertEqual(result.expirations_processed, 1)
        self.assertEqual(result.auto_charged, 0)
        self.assertEqual(len(sender.expirations_sent), 1)

    def test_auto_charge_failure_sets_payment_failed_and_sends_email(self) -> None:
        tenant = make_tenant(
            subscription_status="active",
            plan_cycle_ends_at=_NOW - timedelta(days=1),
            dlocal_payer_id="PAY-1",
        )
        repo = _repo_with(tenant)
        result, sender, _, payments = _run_with_auto_charge(repo, dlocal_status="REJECTED")

        self.assertEqual(result.payment_failed_count, 1)
        self.assertEqual(tenant.subscription_status, "payment_failed")
        self.assertEqual(payments.reconciliation_markers, {})
        self.assertEqual(len(sender.payment_failed_sent), 1)

    def test_payment_failed_retry_within_grace_does_not_resend_email(self) -> None:
        tenant = make_tenant(
            subscription_status="payment_failed",
            plan_cycle_ends_at=_NOW - timedelta(days=1),
            dlocal_payer_id="PAY-1",
        )
        repo = _repo_with(tenant)
        result, sender, dlocal, payments = _run_with_auto_charge(repo, dlocal_status="REJECTED")

        self.assertEqual(result.payment_failed_count, 1)
        self.assertEqual(dlocal.calls, 1)
        self.assertEqual(payments.reconciliation_markers, {})
        self.assertEqual(len(sender.payment_failed_sent), 0)

    def test_payment_failed_grace_expired_forces_expire(self) -> None:
        expired_at = _NOW - timedelta(days=_PAYMENT_FAILED_GRACE_DAYS + 1)
        tenant = make_tenant(
            subscription_status="payment_failed",
            plan_cycle_ends_at=expired_at,
            dlocal_payer_id="PAY-1",
        )
        repo = _repo_with(tenant)
        result, sender, dlocal, _ = _run_with_auto_charge(repo)

        self.assertEqual(result.expirations_processed, 1)
        self.assertEqual(result.auto_charged, 0)
        self.assertEqual(dlocal.calls, 0)
        self.assertEqual(tenant.subscription_status, "expired")
        self.assertEqual(len(sender.expirations_sent), 1)

    def test_payment_failed_without_payer_id_expires_immediately(self) -> None:
        tenant = make_tenant(
            subscription_status="payment_failed",
            plan_cycle_ends_at=_NOW - timedelta(days=1),
            dlocal_payer_id=None,
        )
        repo = _repo_with(tenant)
        result, sender, dlocal, _ = _run_with_auto_charge(repo)

        self.assertEqual(result.expirations_processed, 1)
        self.assertEqual(dlocal.calls, 0)
        self.assertEqual(tenant.subscription_status, "expired")

    def test_payment_failed_retry_success_activates(self) -> None:
        tenant = make_tenant(
            subscription_status="payment_failed",
            plan_cycle_ends_at=_NOW - timedelta(days=1),
            dlocal_payer_id="PAY-1",
        )
        repo = _repo_with(tenant)
        result, _, dlocal, payments = _run_with_auto_charge(repo, dlocal_status="PAID")

        self.assertEqual(result.auto_charged, 1)
        self.assertEqual(dlocal.calls, 1)
        self.assertEqual(payments.saved, [])
        self.assertEqual(len(payments.transact_payments), 1)
        self.assertEqual(len(repo.commit_calls), 1)
        self.assertEqual(payments.reconciliation_markers, {})
        self.assertEqual(tenant.subscription_status, "active")

    def test_auto_charge_commit_failure_does_not_count_success(self) -> None:
        tenant = make_tenant(
            subscription_status="active",
            plan_cycle_ends_at=_NOW - timedelta(days=1),
            dlocal_payer_id="PAY-1",
        )
        repo = _repo_with(tenant)
        repo.commit_errors.append(OptimisticLockError())

        result, sender, dlocal, payments = _run_with_auto_charge(repo, dlocal_status="PAID")

        self.assertEqual(result.auto_charged, 0)
        self.assertEqual(result.auto_charge_reconciliation_required_count, 1)
        self.assertEqual(dlocal.calls, 1)
        self.assertEqual(payments.saved, [])
        self.assertEqual(len(payments.transact_payments), 1)
        self.assertEqual(len(repo.commit_calls), 1)
        self.assertEqual(len(payments.reconciliation_markers), 1)
        marker = next(iter(payments.reconciliation_markers.values()))
        self.assertEqual(marker["payment"].order_id, "DP-auto-1")
        self.assertEqual(marker["reason"], "OptimisticLockError")
        self.assertEqual(len(sender.reconciliation_alerts_sent), 1)
        self.assertEqual(sender.reconciliation_alerts_sent[0]["order_id"], "DP-auto-1")

    def test_auto_charge_dlocal_error_keeps_marker_and_skips_local_mutation(self) -> None:
        import urllib.error

        tenant = make_tenant(
            subscription_status="active",
            plan_cycle_ends_at=_NOW - timedelta(days=1),
            dlocal_payer_id="PAY-1",
        )
        repo = _repo_with(tenant)

        result, sender, dlocal, payments = _run_with_auto_charge(
            repo,
            dlocal_raises=urllib.error.URLError("timeout"),
        )

        self.assertEqual(result.auto_charged, 0)
        self.assertEqual(result.payment_failed_count, 0)
        self.assertEqual(result.auto_charge_reconciliation_required_count, 1)
        self.assertEqual(dlocal.calls, 1)
        self.assertEqual(repo.save_calls, [])
        self.assertEqual(repo.commit_calls, [])
        self.assertEqual(len(payments.reconciliation_markers), 1)
        marker = next(iter(payments.reconciliation_markers.values()))
        self.assertEqual(marker["reason"], "URLError")
        self.assertEqual(len(sender.payment_failed_sent), 0)
        self.assertEqual(len(sender.reconciliation_alerts_sent), 1)
        self.assertEqual(sender.reconciliation_alerts_sent[0]["reason"], "URLError")

    def test_auto_charge_reconciliation_marker_skips_duplicate_charge(self) -> None:
        tenant = make_tenant(
            subscription_status="active",
            plan_cycle_ends_at=_NOW - timedelta(days=1),
            dlocal_payer_id="PAY-1",
        )
        repo = _repo_with(tenant)
        catalog, dlocal, payments = _auto_charge_deps(dlocal_status="PAID")
        payments.reconciliation_markers[(tenant.id, tenant.plan_cycle_ends_at)] = {
            "payment": None,
            "reason": "OptimisticLockError",
        }
        sender = FakeEmailSender()

        result = NotifySubscriptionRenewalUseCase(
            repo,
            sender,
            now=_NOW,
            frontend_url="https://billing.example.com",
            plan_catalog=catalog,
            dlocal=dlocal,
            payment_repo=payments,
            reconciliation_notifier=sender,
            reconciliation_email="billing@example.com",
        ).execute()

        self.assertEqual(result.auto_charged, 0)
        self.assertEqual(result.auto_charge_reconciliation_required_count, 1)
        self.assertEqual(dlocal.calls, 0)
        self.assertEqual(payments.saved, [])
        self.assertEqual(payments.transact_payments, [])
        self.assertEqual(repo.commit_calls, [])
        self.assertEqual(len(sender.reconciliation_alerts_sent), 1)
        self.assertEqual(
            sender.reconciliation_alerts_sent[0]["reason"],
            "AUTO_RENEWAL_MARKER_EXISTS",
        )


if __name__ == "__main__":
    unittest.main()
