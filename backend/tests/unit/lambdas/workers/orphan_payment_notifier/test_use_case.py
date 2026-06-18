from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from lambdas.workers.email_notifications.ports import EmailSender
from lambdas.workers.orphan_payment_notifier.use_case import (
    IOrphanPaymentQuery,
    NotifyOrphanPaymentsUseCase,
    OrphanPaymentSummary,
)

_NOW = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
_CUTOFF = _NOW - timedelta(minutes=30)


def _payment(order_id: str = "DP-1", **kwargs) -> OrphanPaymentSummary:
    return OrphanPaymentSummary(
        order_id=order_id,
        payer_email=kwargs.get("payer_email", "payer@test.com"),
        plan_id=kwargs.get("plan_id", "plan-basic"),
        amount=kwargs.get("amount", "5.99"),
        currency=kwargs.get("currency", "USD"),
        confirmed_at=kwargs.get("confirmed_at", "2026-06-01T09:00:00+00:00"),
    )


class FakeOrphanQuery(IOrphanPaymentQuery):
    def __init__(self, orphans: list[OrphanPaymentSummary] | None = None) -> None:
        self._orphans = orphans or []
        self.calls: list[datetime] = []

    def list_orphaned_paid(self, *, cutoff: datetime) -> list[OrphanPaymentSummary]:
        self.calls.append(cutoff)
        return self._orphans


class FakeEmailSender(EmailSender):
    def __init__(self, *, raises: bool = False) -> None:
        self.alerts_sent: list[dict] = []
        self._raises = raises

    def send_orphan_payment_alert(
        self,
        *,
        superadmin_email,
        order_id,
        payer_email,
        plan_id,
        amount,
        currency,
        confirmed_at,
    ) -> None:
        if self._raises:
            raise RuntimeError("email error")
        self.alerts_sent.append(
            {
                "superadmin_email": superadmin_email,
                "order_id": order_id,
                "payer_email": payer_email,
                "plan_id": plan_id,
                "amount": amount,
                "currency": currency,
                "confirmed_at": confirmed_at,
            }
        )

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
        self,
        *,
        email,
        legal_rep_name,
        trade_name,
        plan_cycle_ends_at,
        days_remaining,
        renewal_url,
    ):
        raise NotImplementedError

    def send_subscription_expired(self, *, email, legal_rep_name, trade_name, renewal_url):
        raise NotImplementedError

    def send_payment_failed(self, *, email, legal_rep_name, trade_name, renewal_url):
        raise NotImplementedError

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


def _run(
    orphans: list[OrphanPaymentSummary] | None = None,
    email_raises: bool = False,
    superadmin: str = "admin@example.com",
):
    query = FakeOrphanQuery(orphans)
    sender = FakeEmailSender(raises=email_raises)
    result = NotifyOrphanPaymentsUseCase(
        query, sender, superadmin_email=superadmin, now=_CUTOFF
    ).execute()
    return result, query, sender


class NotifyOrphanPaymentsUseCaseTests(unittest.TestCase):
    def test_sends_alert_for_each_orphan(self) -> None:
        orphans = [_payment("DP-1"), _payment("DP-2")]
        result, _, sender = _run(orphans)

        self.assertEqual(result.alerts_sent, 2)
        self.assertEqual(len(sender.alerts_sent), 2)
        order_ids = [a["order_id"] for a in sender.alerts_sent]
        self.assertIn("DP-1", order_ids)
        self.assertIn("DP-2", order_ids)

    def test_alert_contains_correct_fields(self) -> None:
        orphan = _payment(
            "DP-99",
            payer_email="buyer@ec.com",
            plan_id="plan-pro",
            amount="12.00",
            currency="USD",
            confirmed_at="2026-06-01T08:00:00+00:00",
        )
        _, _, sender = _run([orphan], superadmin="ops@myapp.com")

        alert = sender.alerts_sent[0]
        self.assertEqual(alert["superadmin_email"], "ops@myapp.com")
        self.assertEqual(alert["order_id"], "DP-99")
        self.assertEqual(alert["payer_email"], "buyer@ec.com")
        self.assertEqual(alert["plan_id"], "plan-pro")
        self.assertEqual(alert["amount"], "12.00")
        self.assertEqual(alert["currency"], "USD")

    def test_passes_cutoff_to_query(self) -> None:
        _, query, _ = _run()
        self.assertEqual(query.calls, [_CUTOFF])

    def test_returns_zero_when_no_orphans(self) -> None:
        result, _, sender = _run([])
        self.assertEqual(result.alerts_sent, 0)
        self.assertEqual(sender.alerts_sent, [])

    def test_continues_on_email_error(self) -> None:
        orphans = [_payment("DP-1"), _payment("DP-2")]
        result, _, _ = _run(orphans, email_raises=True)
        self.assertEqual(result.alerts_sent, 0)

    def test_handles_none_payer_email(self) -> None:
        orphan = _payment("DP-1", payer_email=None)
        result, _, sender = _run([orphan])
        self.assertEqual(result.alerts_sent, 1)
        self.assertIsNone(sender.alerts_sent[0]["payer_email"])


if __name__ == "__main__":
    unittest.main()
