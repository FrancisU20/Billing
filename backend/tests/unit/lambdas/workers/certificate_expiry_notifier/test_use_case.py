from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from lambdas.workers.certificate_expiry_notifier.use_case import (
    NotifyCertificateExpiryUseCase,
)
from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import OptimisticLockError
from tests.unit.support import FakeTenantRepository, make_tenant


class FakeEmailSender(EmailSender):
    def __init__(self) -> None:
        self.certificate_expiry_alerts_sent: list[dict] = []

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
        self.certificate_expiry_alerts_sent.append(
            {
                "email": email,
                "legal_rep_name": legal_rep_name,
                "trade_name": trade_name,
                "ruc": ruc,
                "cert_expires_at": cert_expires_at,
                "days_remaining": days_remaining,
            }
        )

    def send_subscription_renewal_reminder(
        self, *, email, legal_rep_name, trade_name, plan_cycle_ends_at, days_remaining
    ):
        raise NotImplementedError

    def send_subscription_expired(self, *, email, legal_rep_name, trade_name):
        raise NotImplementedError


class NotifyCertificateExpiryUseCaseTests(unittest.TestCase):
    def test_no_candidates_sends_no_alerts(self) -> None:
        now = datetime.now(UTC)
        repo = FakeTenantRepository()
        sender = FakeEmailSender()

        result = NotifyCertificateExpiryUseCase(repo, sender, now=now).execute()

        self.assertEqual(result.tenants_notified, 0)
        self.assertEqual(result.alerts_sent, 0)
        self.assertEqual(sender.certificate_expiry_alerts_sent, [])

    def test_sends_single_alert_for_60_day_threshold(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(id="tenant-1", cert_expires_at=now + timedelta(days=45))
        repo = FakeTenantRepository()
        repo.certificate_expiry_due = [tenant]
        sender = FakeEmailSender()

        result = NotifyCertificateExpiryUseCase(repo, sender, now=now).execute()

        self.assertEqual(result.tenants_notified, 1)
        self.assertEqual(result.alerts_sent, 1)
        self.assertEqual(sender.certificate_expiry_alerts_sent[0]["days_remaining"], 45)
        self.assertEqual(repo.tenants["tenant-1"].cert_expiry_alert_60_sent_at, now)
        self.assertIsNone(repo.tenants["tenant-1"].cert_expiry_alert_30_sent_at)

    def test_sends_both_alerts_in_same_run_when_both_thresholds_due(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(id="tenant-1", cert_expires_at=now + timedelta(days=10))
        repo = FakeTenantRepository()
        repo.certificate_expiry_due = [tenant]
        sender = FakeEmailSender()

        result = NotifyCertificateExpiryUseCase(repo, sender, now=now).execute()

        self.assertEqual(result.tenants_notified, 1)
        self.assertEqual(result.alerts_sent, 2)
        days_remaining = [a["days_remaining"] for a in sender.certificate_expiry_alerts_sent]
        self.assertEqual(days_remaining, [10, 10])
        self.assertEqual(repo.tenants["tenant-1"].cert_expiry_alert_60_sent_at, now)
        self.assertEqual(repo.tenants["tenant-1"].cert_expiry_alert_30_sent_at, now)

    def test_skips_tenant_with_no_due_thresholds(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(id="tenant-1", cert_expires_at=now + timedelta(days=90))
        repo = FakeTenantRepository()
        repo.certificate_expiry_due = [tenant]
        sender = FakeEmailSender()

        result = NotifyCertificateExpiryUseCase(repo, sender, now=now).execute()

        self.assertEqual(result.tenants_notified, 0)
        self.assertEqual(result.alerts_sent, 0)
        self.assertEqual(sender.certificate_expiry_alerts_sent, [])
        self.assertEqual(repo.save_calls, [])

    def test_optimistic_lock_error_on_save_does_not_stop_other_tenants(self) -> None:
        now = datetime.now(UTC)
        failing_tenant = make_tenant(id="tenant-1", cert_expires_at=now + timedelta(days=45))
        other_tenant = make_tenant(id="tenant-2", cert_expires_at=now + timedelta(days=45))
        repo = FakeTenantRepository()
        repo.certificate_expiry_due = [failing_tenant, other_tenant]
        repo.save_errors["tenant-1"] = OptimisticLockError()
        sender = FakeEmailSender()

        result = NotifyCertificateExpiryUseCase(repo, sender, now=now).execute()

        self.assertEqual(result.tenants_notified, 1)
        self.assertEqual(result.alerts_sent, 2)
        self.assertNotIn("tenant-1", repo.tenants)
        self.assertEqual(repo.tenants["tenant-2"].cert_expiry_alert_60_sent_at, now)


if __name__ == "__main__":
    unittest.main()
