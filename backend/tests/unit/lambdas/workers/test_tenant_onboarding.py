from __future__ import annotations

import importlib
import json
import os
import sys
import unittest

from lambdas.workers.tenant_onboarding.events import OwnerCreatedEvent
from lambdas.workers.tenant_onboarding.ports import EventPublisherPort
from lambdas.workers.tenant_onboarding.use_case import OnboardTenantUseCase
from shared.domain.events.domain_event import DomainEvent
from shared.errors import ValidationError
from shared.logger import clear_invocation_context
from tests.unit.support import LambdaContext, configure_unit_environment

# ── Fakes ─────────────────────────────────────────────────────────────────────


class FakeIdentityProvider:
    def __init__(self, *, already_exists: bool = False, reset_allowed: bool = False) -> None:
        self.created_owners: list[dict] = []
        self._already_exists = already_exists
        self._reset_allowed = reset_allowed
        self.reset_passwords: list[dict] = []

    def create_owner(self, *, tenant_id: str, email: str, temporary_password: str) -> bool:
        if self._already_exists:
            return False
        self.created_owners.append(
            {
                "tenant_id": tenant_id,
                "email": email,
            }
        )
        return True

    def reset_temporary_password(self, *, email: str, temporary_password: str) -> bool:
        if not self._reset_allowed:
            return False
        self.reset_passwords.append(
            {
                "email": email,
                "password_length": len(temporary_password),
            }
        )
        return True


class FakeEventPublisher(EventPublisherPort):
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    def publish(self, event: DomainEvent) -> None:
        self.published.append(event)


# ── Use case ──────────────────────────────────────────────────────────────────


class OnboardTenantUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_invocation_context()

    def test_returns_temp_password_when_owner_created(self) -> None:
        idp = FakeIdentityProvider()
        result = OnboardTenantUseCase(idp).execute(
            tenant_id="tenant-1",
            email="owner@codelabs.com",
            legal_rep_name="Owner",
        )
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result), 16)
        self.assertEqual(len(idp.created_owners), 1)

    def test_returns_none_when_existing_user_completed_onboarding(self) -> None:
        idp = FakeIdentityProvider(already_exists=True)
        result = OnboardTenantUseCase(idp).execute(
            tenant_id="tenant-1",
            email="owner@codelabs.com",
            legal_rep_name="Owner",
        )
        self.assertIsNone(result)
        self.assertEqual(idp.reset_passwords, [])

    def test_resets_password_when_existing_user_is_still_onboarding(self) -> None:
        idp = FakeIdentityProvider(already_exists=True, reset_allowed=True)
        result = OnboardTenantUseCase(idp).execute(
            tenant_id="tenant-1",
            email="owner@codelabs.com",
            legal_rep_name="Owner",
        )
        self.assertIsNotNone(result)
        self.assertEqual(idp.reset_passwords[0]["email"], "owner@codelabs.com")
        self.assertEqual(idp.reset_passwords[0]["password_length"], len(result))

    def test_raises_validation_when_tenant_id_missing(self) -> None:
        with self.assertRaises(ValidationError):
            OnboardTenantUseCase(FakeIdentityProvider()).execute(
                tenant_id="",
                email="owner@codelabs.com",
                legal_rep_name="Owner",
            )

    def test_raises_validation_when_email_missing(self) -> None:
        with self.assertRaises(ValidationError):
            OnboardTenantUseCase(FakeIdentityProvider()).execute(
                tenant_id="tenant-1",
                email="",
                legal_rep_name="Owner",
            )

    def test_temp_password_meets_cognito_policy(self) -> None:
        idp = FakeIdentityProvider()
        pwd = OnboardTenantUseCase(idp).execute(
            tenant_id="tenant-1",
            email="owner@codelabs.com",
            legal_rep_name="Owner",
        )
        self.assertTrue(any(c.isupper() for c in pwd))
        self.assertTrue(any(c.islower() for c in pwd))
        self.assertTrue(any(c.isdigit() for c in pwd))
        self.assertTrue(any(c in "!@#$%^&*" for c in pwd))


# ── Handler ───────────────────────────────────────────────────────────────────


class TenantOnboardingHandlerTests(unittest.TestCase):
    def _load_handler_module(self):
        configure_unit_environment()
        os.environ["COGNITO_USER_POOL_ID"] = "unit-user-pool"
        os.environ["EMAIL_NOTIFICATIONS_QUEUE_URL"] = ""
        sys.modules.pop("lambdas.workers.tenant_onboarding.handler", None)
        return importlib.import_module("lambdas.workers.tenant_onboarding.handler")

    def _make_sqs_event(self, data: dict) -> dict:
        return {
            "Records": [
                {
                    "messageId": "msg-1",
                    "receiptHandle": "receipt-1",
                    "attributes": {},
                    "body": json.dumps(
                        {
                            "event_type": "TenantCreatedEvent",
                            "data": data,
                        }
                    ),
                }
            ]
        }

    def test_creates_owner_and_publishes_owner_created_event(self) -> None:
        mod = self._load_handler_module()
        idp = FakeIdentityProvider()
        publisher = FakeEventPublisher()
        mod._identity_provider = idp
        mod._event_publisher = publisher

        result = mod.handler(
            self._make_sqs_event(
                {
                    "tenant_id": "tenant-1",
                    "email": "owner@codelabs.com",
                    "legal_rep_name": "Owner Apellido",
                }
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(idp.created_owners), 1)
        self.assertEqual(len(publisher.published), 1)
        event = publisher.published[0]
        self.assertIsInstance(event, OwnerCreatedEvent)
        self.assertEqual(event.tenant_id, "tenant-1")
        self.assertEqual(event.email, "owner@codelabs.com")
        self.assertGreater(len(event.temp_password), 0)

    def test_does_not_publish_event_when_existing_user_completed_onboarding(self) -> None:
        mod = self._load_handler_module()
        idp = FakeIdentityProvider(already_exists=True)
        publisher = FakeEventPublisher()
        mod._identity_provider = idp
        mod._event_publisher = publisher

        result = mod.handler(
            self._make_sqs_event(
                {
                    "tenant_id": "tenant-1",
                    "email": "owner@codelabs.com",
                    "legal_rep_name": "Owner",
                }
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(publisher.published, [])

    def test_publishes_event_when_existing_user_password_was_reset(self) -> None:
        mod = self._load_handler_module()
        idp = FakeIdentityProvider(already_exists=True, reset_allowed=True)
        publisher = FakeEventPublisher()
        mod._identity_provider = idp
        mod._event_publisher = publisher

        result = mod.handler(
            self._make_sqs_event(
                {
                    "tenant_id": "tenant-1",
                    "email": "owner@codelabs.com",
                    "legal_rep_name": "Owner",
                }
            ),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(publisher.published), 1)
        self.assertGreater(len(publisher.published[0].temp_password), 0)

    def test_ignores_unknown_events(self) -> None:
        mod = self._load_handler_module()
        publisher = FakeEventPublisher()
        mod._event_publisher = publisher

        result = mod.handler(
            {
                "Records": [
                    {
                        "messageId": "msg-1",
                        "receiptHandle": "r",
                        "attributes": {},
                        "body": json.dumps({"event_type": "TenantUpdatedEvent", "data": {}}),
                    }
                ]
            },
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(publisher.published, [])


if __name__ == "__main__":
    unittest.main()
