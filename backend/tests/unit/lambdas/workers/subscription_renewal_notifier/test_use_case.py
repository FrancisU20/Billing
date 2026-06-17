from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from lambdas.workers.email_notifications.ports import EmailSender
from lambdas.workers.subscription_renewal_notifier.use_case import (
    NotifySubscriptionRenewalUseCase,
)
from shared.errors import OptimisticLockError
from tests.unit.support import FakeTenantRepository, make_tenant


class FakeEmailSender(EmailSender):
    def __init__(self) -> None:
        self.reminders_sent: list[dict] = []
        self.expirations_sent: list[dict] = []

    def send_onboarding_otp(self, *, email, legal_rep_name, otp, expires_at):
        raise NotImplementedError

    def send_welcome(self, *, email, legal_rep_name, temp_password):
        raise NotImplementedError

    def send_enterprise_lead_notification(
        self, *, superadmin_email, trade_name, ruc, email, plan_id
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

    def send_orphan_payment_alert(
        self, *, superadmin_email, order_id, payer_email, plan_id, amount, currency, confirmed_at
    ):
        raise NotImplementedError


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


if __name__ == "__main__":
    unittest.main()
