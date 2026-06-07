from __future__ import annotations

import json
import importlib
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
        self._should_fail = should_fail

    def send_welcome(
        self, *, email: str, legal_rep_name: str, temp_password: str
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Brevo unavailable")
        self.sent.append({
            "email":            email,
            "legal_rep_name": legal_rep_name,
            "temp_password":    temp_password,
        })


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
        os.environ["BREVO_SECRET_NAME"]  = "dummy-secret"
        os.environ["BREVO_SENDER_EMAIL"] = "noreply@test.com"
        os.environ["BREVO_SENDER_NAME"]  = "Test"
        sys.modules.pop("lambdas.workers.email_notifications.handler", None)
        return importlib.import_module("lambdas.workers.email_notifications.handler")

    def _make_sqs_event(self, data: dict, event_type: str = "OwnerCreatedEvent") -> dict:
        return {
            "Records": [{
                "messageId":     "msg-1",
                "receiptHandle": "receipt-1",
                "attributes":    {},
                "body": json.dumps({"event_type": event_type, "data": data}),
            }]
        }

    def test_processes_owner_created_event_and_sends_email(self) -> None:
        mod    = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event({
                "email":            "owner@empresa.com",
                "legal_rep_name": "Juan Pérez",
                "temp_password":    "Temp#1234!XY",
            }),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(sender.sent), 1)
        self.assertEqual(sender.sent[0]["email"], "owner@empresa.com")

    def test_ignores_unknown_events_without_error(self) -> None:
        mod    = self._load_handler_module()
        sender = FakeEmailSender()
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event({}, event_type="TenantUpdatedEvent"),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(sender.sent, [])

    def test_brevo_failure_marks_record_as_batch_failure(self) -> None:
        mod    = self._load_handler_module()
        sender = FakeEmailSender(should_fail=True)
        mod._email_sender = sender

        result = mod.handler(
            self._make_sqs_event({
                "email":            "owner@empresa.com",
                "legal_rep_name": "Juan",
                "temp_password":    "Temp#1234!XY",
            }),
            LambdaContext(),
        )

        self.assertEqual(len(result["batchItemFailures"]), 1)
        self.assertEqual(result["batchItemFailures"][0]["itemIdentifier"], "msg-1")

    def test_partial_batch_failure_only_fails_bad_records(self) -> None:
        mod = self._load_handler_module()
        calls: list[str] = []

        class PartialFakeSender(EmailSender):
            def send_welcome(self, *, email, legal_rep_name, temp_password):
                calls.append(email)
                if email == "bad@empresa.com":
                    raise RuntimeError("Brevo timeout")

        mod._email_sender = PartialFakeSender()

        result = mod.handler(
            {
                "Records": [
                    {
                        "messageId": "msg-ok", "receiptHandle": "r1", "attributes": {},
                        "body": json.dumps({
                            "event_type": "OwnerCreatedEvent",
                            "data": {
                                "email": "ok@empresa.com",
                                "legal_rep_name": "OK",
                                "temp_password": "P#1aB2cD3eF",
                            },
                        }),
                    },
                    {
                        "messageId": "msg-fail", "receiptHandle": "r2", "attributes": {},
                        "body": json.dumps({
                            "event_type": "OwnerCreatedEvent",
                            "data": {
                                "email": "bad@empresa.com",
                                "legal_rep_name": "Bad",
                                "temp_password": "P#1aB2cD3eF",
                            },
                        }),
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
