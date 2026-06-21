from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from shared.certificates.metadata import CertificateMetadata
from tests.unit.support import VALID_RUC, make_tenant


class DueCertificateExpiryAlertsTests(unittest.TestCase):
    def test_returns_empty_when_no_certificate(self) -> None:
        tenant = make_tenant(cert_expires_at=None)

        self.assertEqual(tenant.due_certificate_expiry_alerts(datetime.now(UTC)), [])

    def test_returns_empty_when_expiry_is_far_away(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(cert_expires_at=now + timedelta(days=90))

        self.assertEqual(tenant.due_certificate_expiry_alerts(now), [])

    def test_returns_60_when_within_60_days(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(cert_expires_at=now + timedelta(days=45))

        self.assertEqual(tenant.due_certificate_expiry_alerts(now), [60])

    def test_returns_both_thresholds_when_within_30_days(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(cert_expires_at=now + timedelta(days=10))

        self.assertEqual(tenant.due_certificate_expiry_alerts(now), [60, 30])

    def test_skips_thresholds_already_sent(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(
            cert_expires_at=now + timedelta(days=10),
            cert_expiry_alert_60_sent_at=now - timedelta(days=1),
        )

        self.assertEqual(tenant.due_certificate_expiry_alerts(now), [30])

    def test_returns_empty_when_both_thresholds_already_sent(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(
            cert_expires_at=now + timedelta(days=10),
            cert_expiry_alert_60_sent_at=now - timedelta(days=20),
            cert_expiry_alert_30_sent_at=now - timedelta(days=1),
        )

        self.assertEqual(tenant.due_certificate_expiry_alerts(now), [])


class MarkCertificateExpiryAlertSentTests(unittest.TestCase):
    def test_marks_60_day_threshold(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(cert_expires_at=now + timedelta(days=45))

        tenant.mark_certificate_expiry_alert_sent(60, now, updated_by="user-1")

        self.assertEqual(tenant.cert_expiry_alert_60_sent_at, now)
        self.assertIsNone(tenant.cert_expiry_alert_30_sent_at)

    def test_marks_30_day_threshold(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(cert_expires_at=now + timedelta(days=10))

        tenant.mark_certificate_expiry_alert_sent(30, now, updated_by="user-1")

        self.assertEqual(tenant.cert_expiry_alert_30_sent_at, now)

    def test_raises_for_unsupported_threshold(self) -> None:
        tenant = make_tenant()

        with self.assertRaises(ValueError):
            tenant.mark_certificate_expiry_alert_sent(15, datetime.now(UTC), updated_by="user-1")


class AttachCertificateResetsAlertFlagsTests(unittest.TestCase):
    def test_attach_certificate_resets_alert_flags(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(
            cert_expiry_alert_60_sent_at=now - timedelta(days=20),
            cert_expiry_alert_30_sent_at=now - timedelta(days=1),
        )

        tenant.attach_certificate(
            CertificateMetadata(
                subject_ruc=VALID_RUC,
                expires_at=now + timedelta(days=365),
                issuer="Security Data",
            ),
            secret_arn="arn:aws:secretsmanager:sa-east-1:123:secret:/tenant/certificate",
            uploaded_at=now,
            updated_by="user-1",
        )

        self.assertIsNone(tenant.cert_expiry_alert_60_sent_at)
        self.assertIsNone(tenant.cert_expiry_alert_30_sent_at)


class ApplySubscriptionRenewalTenantTests(unittest.TestCase):
    def test_clears_reminder_flag_on_renewal(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(
            subscription_renewal_reminder_sent_at=now - timedelta(days=2),
            plan_cycle_ends_at=now,
        )

        tenant.apply_subscription_renewal(
            payer_id="PAY-1",
            plan_cycle="month",
            now=now,
            updated_by="user-1",
        )

        self.assertIsNone(tenant.subscription_renewal_reminder_sent_at)

    def test_sets_subscription_status_active(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(subscription_status="expired")

        tenant.apply_subscription_renewal(
            payer_id="PAY-1",
            plan_cycle="month",
            now=now,
            updated_by="user-1",
        )

        self.assertEqual(tenant.subscription_status, "active")

    def test_extends_cycle_from_current_end_date(self) -> None:
        now = datetime.now(UTC)
        future = now + timedelta(days=10)
        tenant = make_tenant(plan_cycle_ends_at=future)

        tenant.apply_subscription_renewal(
            payer_id="PAY-1",
            plan_cycle="month",
            now=now,
            updated_by="user-1",
        )

        # Extended from future (not from now) — base = max(now, future) = future
        self.assertGreater(tenant.plan_cycle_ends_at, future)

    def test_renewal_persists_billing_cycle(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(billing_cycle="month")

        tenant.apply_subscription_renewal(
            payer_id="PAY-1",
            plan_cycle="year",
            now=now,
            updated_by="user-1",
        )

        self.assertEqual(tenant.billing_cycle, "year")


class ActivateSubscriptionTenantTests(unittest.TestCase):
    def test_activation_persists_billing_cycle(self) -> None:
        now = datetime.now(UTC)
        tenant = make_tenant(subscription_status="pending_payment", billing_cycle="month")

        tenant.activate_subscription(
            payer_id="PAY-1",
            plan_cycle="year",
            now=now,
            updated_by="user-1",
        )

        self.assertEqual(tenant.billing_cycle, "year")
        self.assertEqual(tenant.subscription_status, "active")


if __name__ == "__main__":
    unittest.main()
