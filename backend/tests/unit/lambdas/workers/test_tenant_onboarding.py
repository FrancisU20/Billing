from __future__ import annotations

import json
import importlib
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
    def __init__(self, *, already_exists: bool = False) -> None:
        self.created_owners: list[dict] = []
        self._already_exists = already_exists

    def create_owner(self, *, tenant_id: str, email: str, temporary_password: str) -> bool:
        if self._already_exists:
            return False
        self.created_owners.append({
            "tenant_id": tenant_id,
            "email":     email,
        })
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

    def test_retorna_temp_password_cuando_owner_es_creado(self) -> None:
        idp = FakeIdentityProvider()
        result = OnboardTenantUseCase(idp).execute(
            tenant_id="tenant-1",
            email="owner@codelabs.com",
            nombre_rep_legal="Owner",
        )
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result), 16)
        self.assertEqual(len(idp.created_owners), 1)

    def test_retorna_none_cuando_usuario_ya_existe(self) -> None:
        idp = FakeIdentityProvider(already_exists=True)
        result = OnboardTenantUseCase(idp).execute(
            tenant_id="tenant-1",
            email="owner@codelabs.com",
            nombre_rep_legal="Owner",
        )
        self.assertIsNone(result)

    def test_lanza_validacion_si_falta_tenant_id(self) -> None:
        with self.assertRaises(ValidationError):
            OnboardTenantUseCase(FakeIdentityProvider()).execute(
                tenant_id="",
                email="owner@codelabs.com",
                nombre_rep_legal="Owner",
            )

    def test_lanza_validacion_si_falta_email(self) -> None:
        with self.assertRaises(ValidationError):
            OnboardTenantUseCase(FakeIdentityProvider()).execute(
                tenant_id="tenant-1",
                email="",
                nombre_rep_legal="Owner",
            )

    def test_temp_password_cumple_politica_cognito(self) -> None:
        idp = FakeIdentityProvider()
        pwd = OnboardTenantUseCase(idp).execute(
            tenant_id="tenant-1",
            email="owner@codelabs.com",
            nombre_rep_legal="Owner",
        )
        self.assertTrue(any(c.isupper() for c in pwd))
        self.assertTrue(any(c.islower() for c in pwd))
        self.assertTrue(any(c.isdigit() for c in pwd))
        self.assertTrue(any(c in "!@#$%^&*" for c in pwd))


# ── Handler ───────────────────────────────────────────────────────────────────

class TenantOnboardingHandlerTests(unittest.TestCase):
    def _load_handler_module(self):
        configure_unit_environment()
        os.environ["COGNITO_USER_POOL_ID"]          = "unit-user-pool"
        os.environ["EMAIL_NOTIFICATIONS_QUEUE_URL"] = ""
        sys.modules.pop("lambdas.workers.tenant_onboarding.handler", None)
        return importlib.import_module("lambdas.workers.tenant_onboarding.handler")

    def _make_sqs_event(self, data: dict) -> dict:
        return {
            "Records": [{
                "messageId":     "msg-1",
                "receiptHandle": "receipt-1",
                "attributes":    {},
                "body": json.dumps({
                    "event_type": "TenantCreatedEvent",
                    "data":       data,
                }),
            }]
        }

    def test_crea_owner_y_publica_owner_created_event(self) -> None:
        mod = self._load_handler_module()
        idp       = FakeIdentityProvider()
        publisher = FakeEventPublisher()
        mod._identity_provider = idp
        mod._event_publisher   = publisher

        result = mod.handler(
            self._make_sqs_event({
                "tenant_id":        "tenant-1",
                "email":            "owner@codelabs.com",
                "nombre_rep_legal": "Owner Apellido",
            }),
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

    def test_no_publica_evento_si_usuario_ya_existe(self) -> None:
        mod = self._load_handler_module()
        idp       = FakeIdentityProvider(already_exists=True)
        publisher = FakeEventPublisher()
        mod._identity_provider = idp
        mod._event_publisher   = publisher

        result = mod.handler(
            self._make_sqs_event({
                "tenant_id": "tenant-1",
                "email":     "owner@codelabs.com",
                "nombre_rep_legal": "Owner",
            }),
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(publisher.published, [])

    def test_ignora_eventos_desconocidos(self) -> None:
        mod = self._load_handler_module()
        publisher = FakeEventPublisher()
        mod._event_publisher = publisher

        result = mod.handler(
            {
                "Records": [{
                    "messageId": "msg-1", "receiptHandle": "r", "attributes": {},
                    "body": json.dumps({"event_type": "TenantUpdatedEvent", "data": {}}),
                }]
            },
            LambdaContext(),
        )

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(publisher.published, [])


if __name__ == "__main__":
    unittest.main()
