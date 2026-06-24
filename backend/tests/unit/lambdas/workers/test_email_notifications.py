from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from datetime import datetime

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
        self.password_reset_sent: list[dict] = []
        self.enterprise_leads_sent: list[dict] = []
        self.certificate_expiry_alerts_sent: list[dict] = []
        self.renewal_reminders_sent: list[dict] = []
        self.subscription_expired_sent: list[dict] = []
        self.document_authorized_sent: list[dict] = []
        self.document_buyer_sent: list[dict] = []
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

    def send_password_reset(self, *, email: str, code: str, expires_at: str) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.password_reset_sent.append(
            {
                "email": email,
                "code": code,
                "expires_at": expires_at,
            }
        )

    def send_enterprise_lead_notification(
        self,
        *,
        superadmin_email: str,
        trade_name: str,
        ruc: str,
        email: str,
        plan_id: str,
        plan_name: str = "",
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.enterprise_leads_sent.append(
            {
                "superadmin_email": superadmin_email,
                "trade_name": trade_name,
                "ruc": ruc,
                "email": email,
                "plan_name": plan_name,
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
        issuer_name: str,
        issuer_ruc: str,
        buyer_name: str,
        buyer_id: str,
        buyer_email: str,
        sequential_display: str,
        issued_at: str,
        authorized_at: str,
        total: str,
        currency: str,
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
                "issuer_name": issuer_name,
                "issuer_ruc": issuer_ruc,
                "buyer_name": buyer_name,
                "buyer_id": buyer_id,
                "buyer_email": buyer_email,
                "sequential_display": sequential_display,
                "issued_at": issued_at,
                "authorized_at": authorized_at,
                "total": total,
                "currency": currency,
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

    def send_document_to_buyer(
        self,
        *,
        email: str,
        buyer_name: str,
        document_id: str,
        access_key: str,
        authorization_number: str,
        issuer_name: str,
        issuer_ruc: str,
        buyer_id: str,
        issued_at: str,
        authorized_at: str,
        total: str,
        currency: str,
        xml_content: bytes,
        xml_filename: str,
        ride_content: bytes,
        ride_filename: str,
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.document_buyer_sent.append(
            {
                "email": email,
                "buyer_name": buyer_name,
                "document_id": document_id,
                "access_key": access_key,
                "authorization_number": authorization_number,
                "issuer_name": issuer_name,
                "issuer_ruc": issuer_ruc,
                "buyer_id": buyer_id,
                "issued_at": issued_at,
                "authorized_at": authorized_at,
                "total": total,
                "currency": currency,
                "xml_content": xml_content,
                "xml_filename": xml_filename,
                "ride_content": ride_content,
                "ride_filename": ride_filename,
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
        os.environ["SUPERADMIN_EMAIL"] = "admin@codelabsecuador.com"
        os.environ["SALES_EMAIL"] = "sales@codelabsecuador.com"
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

    def test_processes_password_reset_event_and_sends_email(self) -> None:
        mod = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event(
                {
                    "email": "owner@empresa.com",
                    "code": "123456",
                    "expires_at": "2026-06-13T12:00:00+00:00",
                },
                event_type="PasswordResetRequestedEvent",
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.password_reset_sent), 1)
        self.assertEqual(sender.password_reset_sent[0]["email"], "owner@empresa.com")
        self.assertEqual(sender.password_reset_sent[0]["code"], "123456")

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
                    "plan_id": "uuid-corporativo",
                    "plan_name": "Corporativo",
                },
                event_type="EnterpriseLeadCreatedEvent",
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.enterprise_leads_sent), 1)
        sent = sender.enterprise_leads_sent[0]
        self.assertEqual(sent["superadmin_email"], "sales@codelabsecuador.com")
        self.assertEqual(sent["trade_name"], "Empresa Demo S.A.")
        self.assertEqual(sent["ruc"], "1792146739001")
        self.assertEqual(sent["plan_name"], "Corporativo")

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
                    "issuer_name": "Empresa Demo S.A.",
                    "issuer_ruc": "1792146739001",
                    "buyer_name": "Cliente Demo",
                    "buyer_id": "1712345678",
                    "buyer_email": "buyer@example.com",
                    "sequential_display": "001-001-000000001",
                    "issued_at": "2026-06-18",
                    "authorized_at": "2026-06-18T22:00:00+00:00",
                    "total": "10.00",
                    "currency": "USD",
                },
                event_type="DocumentAuthorizedEvent",
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.document_authorized_sent), 1)
        sent = sender.document_authorized_sent[0]
        self.assertEqual(sent["document_id"], "d1")
        self.assertEqual(sent["issuer_name"], "Empresa Demo S.A.")
        self.assertEqual(sent["buyer_id"], "1712345678")
        self.assertEqual(sent["sequential_display"], "001-001-000000001")
        self.assertEqual(sent["total"], "10.00")

    def test_processes_document_buyer_notification_event(self) -> None:
        from lambdas.documents.domain.entities import DocumentStatus
        from lambdas.workers.email_notifications.ports import DocumentAttachments
        from tests.unit.lambdas.invoice_processor.fixtures import make_document

        class FakeDocumentsRepository:
            def __init__(self) -> None:
                self.document = make_document(
                    document_id="d1",
                    tenant_id="t1",
                    status=DocumentStatus.AUTHORIZED,
                    buyer_email="buyer@example.com",
                    buyer_name="Cliente Demo",
                    buyer_id="1712345678",
                    authorization_number="123",
                    authorized_at=datetime.fromisoformat("2026-06-18T22:00:00+00:00"),
                    xml_s3_key="x.xml",
                    ride_s3_key="r.pdf",
                )

            def get(self, tenant_id, document_id):
                return self.document

            def begin_buyer_notification(self, tenant_id, document_id):
                return True

            def mark_buyer_notification_status(self, tenant_id, document_id, **kwargs):
                return True

        class FakeAttachmentReader:
            def get_authorized_document(self, **kwargs):
                return DocumentAttachments(
                    xml_content=b"<factura/>",
                    xml_filename="d1.xml",
                    ride_content=b"%PDF",
                    ride_filename="d1.pdf",
                )

        mod = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender
        mod._documents_repo = FakeDocumentsRepository()
        mod._attachment_reader = FakeAttachmentReader()

        result = mod.handler(
            self._make_sqs_event(
                {
                    "tenant_id": "t1",
                    "document_id": "d1",
                    "issuer_name": "Empresa Demo S.A.",
                    "issuer_ruc": "1792146739001",
                },
                event_type="DocumentBuyerNotificationRequestedEvent",
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.document_buyer_sent), 1)
        sent = sender.document_buyer_sent[0]
        self.assertEqual(sent["email"], "buyer@example.com")
        self.assertEqual(sent["issuer_name"], "Empresa Demo S.A.")
        self.assertEqual(sent["issuer_ruc"], "1792146739001")
        self.assertEqual(sent["buyer_id"], "1712345678")
        self.assertEqual(sent["authorized_at"], "2026-06-18T17:00:00-05:00")

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
                self,
                *,
                email,
                legal_rep_name,
                document_id,
                access_key,
                authorization_number,
                issuer_name,
                issuer_ruc,
                buyer_name,
                buyer_id,
                buyer_email,
                sequential_display,
                issued_at,
                authorized_at,
                total,
                currency,
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

            def send_document_to_buyer(
                self,
                *,
                email,
                buyer_name,
                document_id,
                access_key,
                authorization_number,
                issuer_name,
                issuer_ruc,
                buyer_id,
                issued_at,
                authorized_at,
                total,
                currency,
                xml_content,
                xml_filename,
                ride_content,
                ride_filename,
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
