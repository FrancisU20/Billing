from __future__ import annotations

import importlib
import json
import os
import sys
import unittest

from lambdas.workers.email_notifications.ports import EmailSender
from lambdas.workers.email_notifications.use_cases.send_welcome_email import (
    SendWelcomeEmailUseCase,
)
from shared.errors import InternalError, ValidationError
from shared.logger import clear_invocation_context
from tests.unit.support import LambdaContext, configure_unit_environment

# ── Fakes ─────────────────────────────────────────────────────────────────────


class FakeEmailSender(EmailSender):
    def __init__(self, *, should_fail: bool = False) -> None:
        self.sent: list[dict] = []
        self.otp_sent: list[dict] = []
        self.enterprise_leads_sent: list[dict] = []
        self.certificate_expiry_alerts_sent: list[dict] = []
        self.renewal_reminders_sent: list[dict] = []
        self.subscription_expired_sent: list[dict] = []
        self.document_authorized_sent: list[dict] = []
        self.document_rejected_sent: list[dict] = []
        self.document_failed_permanent_sent: list[dict] = []
        self._should_fail = should_fail

    def send_onboarding_otp(
        self, *, email: str, legal_rep_name: str, otp: str, expires_at: str
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.otp_sent.append(
            {
                "email": email,
                "legal_rep_name": legal_rep_name,
                "otp": otp,
                "expires_at": expires_at,
            }
        )

    def send_welcome(self, *, email: str, legal_rep_name: str, temp_password: str) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.sent.append(
            {
                "email": email,
                "legal_rep_name": legal_rep_name,
                "temp_password": temp_password,
            }
        )

    def send_enterprise_lead_notification(
        self, *, superadmin_email: str, trade_name: str, ruc: str, email: str, plan_id: str
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.enterprise_leads_sent.append(
            {
                "superadmin_email": superadmin_email,
                "trade_name": trade_name,
                "ruc": ruc,
                "email": email,
                "plan_id": plan_id,
            }
        )

    def send_certificate_expiry_alert(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        ruc: str,
        cert_expires_at: str,
        days_remaining: int,
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
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
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        plan_cycle_ends_at: str,
        days_remaining: int,
        renewal_url: str,
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.renewal_reminders_sent.append(
            {
                "email": email,
                "legal_rep_name": legal_rep_name,
                "trade_name": trade_name,
                "plan_cycle_ends_at": plan_cycle_ends_at,
                "days_remaining": days_remaining,
                "renewal_url": renewal_url,
            }
        )

    def send_subscription_expired(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        renewal_url: str,
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.subscription_expired_sent.append(
            {
                "email": email,
                "legal_rep_name": legal_rep_name,
                "trade_name": trade_name,
            }
        )

    def send_payment_failed(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        renewal_url: str,
    ) -> None:
        raise NotImplementedError

    def send_document_authorized(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
        authorization_number: str,
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.document_authorized_sent.append(
            {
                "email": email,
                "legal_rep_name": legal_rep_name,
                "document_id": document_id,
                "access_key": access_key,
                "authorization_number": authorization_number,
            }
        )

    def send_document_rejected(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
        sri_errors: list[dict],
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.document_rejected_sent.append(
            {
                "email": email,
                "legal_rep_name": legal_rep_name,
                "document_id": document_id,
                "access_key": access_key,
                "sri_errors": sri_errors,
            }
        )

    def send_document_failed_permanent(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.document_failed_permanent_sent.append(
            {
                "email": email,
                "legal_rep_name": legal_rep_name,
                "document_id": document_id,
                "access_key": access_key,
            }
        )

    def send_orphan_payment_alert(
        self,
        *,
        superadmin_email: str,
        order_id: str,
        payer_email: str | None,
        plan_id: str,
        amount: str,
        currency: str,
        confirmed_at: str,
    ) -> None:
        raise NotImplementedError


# ── Use case ──────────────────────────────────────────────────────────────────


class SendWelcomeEmailUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_invocation_context()

    def test_calls_email_sender_with_correct_data(self) -> None:
        sender = FakeEmailSender()
        SendWelcomeEmailUseCase(sender).execute(
            email="owner@empresa.com",
            legal_rep_name="Juan Pérez",
            temp_password="Temp#1234!XY",
        )
        self.assertEqual(len(sender.sent), 1)
        sent = sender.sent[0]
        self.assertEqual(sent["email"], "owner@empresa.com")
        self.assertEqual(sent["legal_rep_name"], "Juan Pérez")
        self.assertEqual(sent["temp_password"], "Temp#1234!XY")

    def test_raises_validation_when_email_empty(self) -> None:
        with self.assertRaises(ValidationError):
            SendWelcomeEmailUseCase(FakeEmailSender()).execute(
                email="",
                legal_rep_name="Juan",
                temp_password="Temp#1234!XY",
            )

    def test_raises_validation_when_password_empty(self) -> None:
        with self.assertRaises(ValidationError):
            SendWelcomeEmailUseCase(FakeEmailSender()).execute(
                email="owner@empresa.com",
                legal_rep_name="Juan",
                temp_password="",
            )

    def test_brevo_failure_raises_internal_error(self) -> None:
        sender = FakeEmailSender(should_fail=True)
        with self.assertRaises(InternalError):
            SendWelcomeEmailUseCase(sender).execute(
                email="owner@empresa.com",
                legal_rep_name="Juan",
                temp_password="Temp#1234!XY",
            )
        self.assertEqual(sender.sent, [])


# ── Handler ───────────────────────────────────────────────────────────────────


class EmailNotificationsHandlerTests(unittest.TestCase):
    def _load_handler_module(self):
        configure_unit_environment()
        os.environ["BREVO_SECRET_NAME"] = "dummy-secret"
        os.environ["BREVO_SENDER_EMAIL"] = "noreply@test.com"
        os.environ["BREVO_SENDER_NAME"] = "Test"
        os.environ["SUPERADMIN_EMAIL"] = "ventas@codelabsecuador.com"
        sys.modules.pop("lambdas.workers.email_notifications.handler", None)
        return importlib.import_module("lambdas.workers.email_notifications.handler")

    def _make_sqs_event(self, data: dict, event_type: str = "OwnerCreatedEvent") -> dict:
        return {
            "Records": [
                {
                    "messageId": "msg-1",
                    "receiptHandle": "receipt-1",
                    "attributes": {},
                    "body": json.dumps({"event_type": event_type, "data": data}),
                }
            ]
        }

    def test_processes_owner_created_event_and_sends_email(self) -> None:
        mod = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event(
                {
                    "email": "owner@empresa.com",
                    "legal_rep_name": "Juan Pérez",
                    "temp_password": "Temp#1234!XY",
                }
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.sent), 1)
        self.assertEqual(sender.sent[0]["email"], "owner@empresa.com")

    def test_processes_onboarding_otp_event_and_sends_email(self) -> None:
        mod = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event(
                {
                    "email": "owner@empresa.com",
                    "legal_rep_name": "Juan Pérez",
                    "otp": "123456",
                    "expires_at": "2026-06-13T12:00:00+00:00",
                },
                event_type="OnboardingOtpRequestedEvent",
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.otp_sent), 1)
        self.assertEqual(sender.otp_sent[0]["otp"], "123456")

    def test_processes_enterprise_lead_created_event_and_sends_email(self) -> None:
        mod = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event(
                {
                    "trade_name": "Empresa Demo S.A.",
                    "ruc": "1792146739001",
                    "email": "contacto@empresa.com",
                    "plan_id": "uuid-enterprise",
                },
                event_type="EnterpriseLeadCreatedEvent",
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.enterprise_leads_sent), 1)
        sent = sender.enterprise_leads_sent[0]
        self.assertEqual(sent["superadmin_email"], "ventas@codelabsecuador.com")
        self.assertEqual(sent["trade_name"], "Empresa Demo S.A.")
        self.assertEqual(sent["ruc"], "1792146739001")

    def test_ignores_unknown_events_without_error(self) -> None:
        mod = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event({}, event_type="TenantUpdatedEvent"),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(sender.sent, [])

    def test_processes_document_authorized_event_and_sends_email(self) -> None:
        mod = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event(
                {
                    "tenant_id": "t1",
                    "document_id": "d1",
                    "access_key": "1" * 49,
                    "authorization_number": "1" * 49,
                    "tenant_email": "owner@empresa.com",
                    "legal_rep_name": "Juan Pérez",
                },
                event_type="DocumentAuthorizedEvent",
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.document_authorized_sent), 1)
        self.assertEqual(sender.document_authorized_sent[0]["document_id"], "d1")

    def test_processes_document_rejected_event_and_sends_email(self) -> None:
        mod = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event(
                {
                    "tenant_id": "t1",
                    "document_id": "d1",
                    "access_key": "1" * 49,
                    "tenant_email": "owner@empresa.com",
                    "legal_rep_name": "Juan Pérez",
                    "sri_errors": [{"code": "43", "message": "FIRMA INVALIDA"}],
                },
                event_type="DocumentRejectedEvent",
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.document_rejected_sent), 1)
        self.assertEqual(sender.document_rejected_sent[0]["sri_errors"][0]["code"], "43")

    def test_processes_document_failed_permanent_event_and_sends_email(self) -> None:
        mod = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event(
                {
                    "tenant_id": "t1",
                    "document_id": "d1",
                    "access_key": "1" * 49,
                    "tenant_email": "owner@empresa.com",
                    "legal_rep_name": "Juan Pérez",
                },
                event_type="DocumentFailedPermanentEvent",
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.document_failed_permanent_sent), 1)

    def test_brevo_failure_marks_record_as_batch_failure(self) -> None:
        mod = self._load_handler_module()
        sender = FakeEmailSender(should_fail=True)
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event(
                {
                    "email": "owner@empresa.com",
                    "legal_rep_name": "Juan",
                    "temp_password": "Temp#1234!XY",
                }
            ),
            LambdaContext(),
        )

        self.assertEqual(len(result["batchItemFailures"]), 1)
        self.assertEqual(result["batchItemFailures"][0]["itemIdentifier"], "msg-1")

    def test_partial_batch_failure_only_fails_bad_records(self) -> None:
        mod = self._load_handler_module()
        calls: list[str] = []

        class PartialFakeSender(EmailSender):
            def send_onboarding_otp(self, *, email, legal_rep_name, otp, expires_at):
                raise NotImplementedError

            def send_welcome(self, *, email, legal_rep_name, temp_password):
                calls.append(email)
                if email == "bad@empresa.com":
                    raise RuntimeError("Brevo timeout")

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

            def send_document_rejected(
                self, *, email, legal_rep_name, document_id, access_key, sri_errors
            ):
                raise NotImplementedError

            def send_document_failed_permanent(
                self, *, email, legal_rep_name, document_id, access_key
            ):
                raise NotImplementedError

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
            ):
                raise NotImplementedError

        mod._email_sender = PartialFakeSender()

        result = mod.handler(
            {
                "Records": [
                    {
                        "messageId": "msg-ok",
                        "receiptHandle": "r1",
                        "attributes": {},
                        "body": json.dumps(
                            {
                                "event_type": "OwnerCreatedEvent",
                                "data": {
                                    "email": "ok@empresa.com",
                                    "legal_rep_name": "OK",
                                    "temp_password": "P#1aB2cD3eF",
                                },
                            }
                        ),
                    },
                    {
                        "messageId": "msg-fail",
                        "receiptHandle": "r2",
                        "attributes": {},
                        "body": json.dumps(
                            {
                                "event_type": "OwnerCreatedEvent",
                                "data": {
                                    "email": "bad@empresa.com",
                                    "legal_rep_name": "Bad",
                                    "temp_password": "P#1aB2cD3eF",
                                },
                            }
                        ),
                    },
                ]
            },
            LambdaContext(),
        )

        failures = [f["itemIdentifier"] for f in result["batchItemFailures"]]
        self.assertIn("msg-fail", failures)
        self.assertNotIn("msg-ok", failures)
        self.assertIn("ok@empresa.com", calls)
        self.assertIn("bad@empresa.com", calls)


if __name__ == "__main__":
    unittest.main()
