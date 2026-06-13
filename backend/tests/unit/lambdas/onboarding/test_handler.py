from __future__ import annotations

import importlib
import os
import sys
import unittest
from typing import Any
from unittest.mock import patch

from tests.unit.lambdas.onboarding.test_use_cases import FakeOnboardingPlanCatalog
from tests.unit.support import (
    LambdaContext,
    api_event,
    configure_unit_environment,
    decode_response,
    tenant_payload,
)


class FakeEnterpriseLeadRepository:
    def __init__(self) -> None:
        self.commit_calls: list[dict[str, Any]] = []

    def commit(self, **kwargs: Any) -> None:
        self.commit_calls.append(kwargs)


def _load_handler_module():
    configure_unit_environment()
    os.environ["TENANTS_TABLE"] = "unit-tenants"
    os.environ["PLANS_TABLE"] = "unit-plans"
    os.environ["AUDIT_LOG_TABLE"] = "unit-audit"
    os.environ["OUTBOX_TABLE"] = ""
    os.environ.pop("IDEMPOTENCY_TABLE", None)

    sys.modules.pop("lambdas.onboarding.handler", None)
    sys.modules.pop("lambdas._base.idempotency", None)
    return importlib.import_module("lambdas.onboarding.handler")


def _onboarding_event(**overrides: Any) -> dict:
    return api_event(
        method="POST",
        path="/onboarding",
        body=tenant_payload(**overrides),
        headers={"X-Idempotency-Key": "onboarding-1"},
        claims={
            "sub": "",
            "custom:tenant_id": "",
            "custom:role": "viewer",
            "custom:is_superadmin": "false",
        },
    )


class OnboardingHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = _load_handler_module()
        self.context = LambdaContext()

    def test_self_service_plan_creates_tenant(self) -> None:
        from tests.unit.support import FakeTenantRepository

        tenant_repo = FakeTenantRepository()
        idempotency_context = object()
        event = _onboarding_event()

        with (
            patch.object(self.handler, "_tenant_repo", return_value=tenant_repo),
            patch.object(
                self.handler,
                "_plan_catalog",
                return_value=FakeOnboardingPlanCatalog(self_service=True),
            ),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue(body["success"])
        self.assertIn("tenant_id", body["data"])
        self.assertEqual(len(tenant_repo.commit_calls), 1)
        commit = tenant_repo.commit_calls[0]
        self.assertEqual(commit["action"], "CREATE")
        self.assertIs(commit["idempotency"], idempotency_context)
        self.assertEqual(commit["events"][0].event_type, "TenantCreatedEvent")

    def test_non_self_service_plan_creates_enterprise_lead(self) -> None:
        from tests.unit.support import FakeTenantRepository

        tenant_repo = FakeTenantRepository()
        lead_repo = FakeEnterpriseLeadRepository()
        idempotency_context = object()
        event = _onboarding_event()

        with (
            patch.object(self.handler, "_tenant_repo", return_value=tenant_repo),
            patch.object(self.handler, "_lead_repo", return_value=lead_repo),
            patch.object(
                self.handler,
                "_plan_catalog",
                return_value=FakeOnboardingPlanCatalog(self_service=False),
            ),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue(body["success"])
        self.assertIn("message", body["data"])
        self.assertEqual(tenant_repo.commit_calls, [])
        self.assertEqual(len(lead_repo.commit_calls), 1)
        commit = lead_repo.commit_calls[0]
        self.assertIs(commit["idempotency"], idempotency_context)
        self.assertEqual(commit["events"][0].event_type, "EnterpriseLeadCreatedEvent")

    def test_unknown_plan_returns_404(self) -> None:
        from tests.unit.support import FakeTenantRepository

        tenant_repo = FakeTenantRepository()
        event = _onboarding_event()

        with (
            patch.object(self.handler, "_tenant_repo", return_value=tenant_repo),
            patch.object(
                self.handler, "_plan_catalog", return_value=FakeOnboardingPlanCatalog(exists=False)
            ),
            patch.object(self.handler, "require_current_context", return_value=object()),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 404)
        self.assertEqual(body["error"]["code"], "PLAN_NOT_FOUND")
        self.assertEqual(tenant_repo.commit_calls, [])

    def test_unknown_route_returns_404(self) -> None:
        event = api_event(method="GET", path="/does-not-exist")

        response = self.handler.handler(event, self.context)
        body = decode_response(response)

        self.assertEqual(response["statusCode"], 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
