from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from lambdas.plans.domain.errors import PlanNotFoundError
from lambdas.plans.domain.plan import Plan
from lambdas.plans.domain.repositories.i_plan_repository import IPlanRepository
from tests.unit.support import LambdaContext, api_event, configure_unit_environment


# ── Fake ──────────────────────────────────────────────────────────────────────

class FakePlanRepository(IPlanRepository):
    def __init__(self) -> None:
        self._free  = Plan(id="uuid-free", slug="free", name="Free",
                           monthly_price=Decimal("0.00"), document_limit=20,
                           limit_cycle="year", order=0)
        self._basic = Plan(id="uuid-basic", slug="basic", name="Basic",
                           monthly_price=Decimal("5.99"), document_limit=50,
                           limit_cycle="month", order=1)
        self._by_id   = {"uuid-free": self._free, "uuid-basic": self._basic}
        self._by_slug = {"free": self._free, "basic": self._basic}
        self.commit_calls: list[dict[str, Any]] = []

    def get_by_id(self, plan_id: str) -> Plan:
        if plan_id not in self._by_id:
            raise PlanNotFoundError()
        return self._by_id[plan_id]

    def get_by_slug(self, slug: str) -> Plan:
        if slug not in self._by_slug:
            raise PlanNotFoundError()
        return self._by_slug[slug]

    def save(self, plan: Plan) -> None:
        self._by_id[plan.id]     = plan
        self._by_slug[plan.slug] = plan

    def commit(self, **kwargs: Any) -> None:
        self.commit_calls.append(kwargs)
        self.save(kwargs["plan"])

    def list(self, active_only: bool = False) -> list[Plan]:
        return list(self._by_id.values())


# ── Tests ─────────────────────────────────────────────────────────────────────

class PlansHandlerTests(unittest.TestCase):
    def _load(self):
        configure_unit_environment()
        os.environ["PLANS_TABLE"] = "unit-plans"
        os.environ["AUDIT_LOG_TABLE"] = ""
        os.environ.pop("IDEMPOTENCY_TABLE", None)
        sys.modules.pop("lambdas.plans.handler", None)
        sys.modules.pop("lambdas._base.idempotency", None)
        mod       = importlib.import_module("lambdas.plans.handler")
        fake_repo = FakePlanRepository()
        mod._repo = lambda: fake_repo
        self._repo = fake_repo
        return mod

    def test_list_is_public(self) -> None:
        mod    = self._load()
        result = mod.handler(api_event(method="GET", path="/plans"), LambdaContext())
        body   = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertIn("items", body["data"])
        self.assertEqual(len(body["data"]["items"]), 2)

    def test_list_works_for_anonymous_request_without_jwt(self) -> None:
        # Public pricing: no authorizer claims at all → must not 401
        mod   = self._load()
        event = {
            "version": "2.0",
            "rawPath": "/plans",
            "requestContext": {"requestId": "anon-1", "http": {"method": "GET", "path": "/plans"}},
            "headers": {},
            "queryStringParameters": None,
            "pathParameters": None,
            "body": None,
            "isBase64Encoded": False,
        }
        result = mod.handler(event, LambdaContext())
        self.assertEqual(result["statusCode"], 200)

    def test_get_by_slug_returns_plan(self) -> None:
        mod    = self._load()
        result = mod.handler(api_event(method="GET", path="/plans/free"), LambdaContext())
        body   = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(body["data"]["slug"], "free")
        self.assertEqual(body["data"]["id"], "uuid-free")

    def test_get_missing_slug_returns_404(self) -> None:
        mod    = self._load()
        result = mod.handler(api_event(method="GET", path="/plans/missing"), LambdaContext())
        body   = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 404)
        self.assertEqual(body["error"]["code"], "PLAN_NOT_FOUND")

    def test_create_requires_superadmin(self) -> None:
        mod   = self._load()
        event = api_event(
            method="POST", path="/plans",
            body={"slug": "pro", "name": "Pro", "document_limit": 1000,
                  "monthly_price": 29.99, "annual_price": 287.0, "limit_cycle": "month"},
            claims={"sub": "u1", "custom:role": "owner",
                    "custom:is_superadmin": "false", "custom:tenant_id": "t1"},
        )
        self.assertEqual(mod.handler(event, LambdaContext())["statusCode"], 403)

    def test_create_superadmin_generates_uuid_as_pk(self) -> None:
        mod    = self._load()
        idempotency_context = object()
        with patch.object(mod, "require_current_context", return_value=idempotency_context):
            result = mod.handler(api_event(
                method="POST", path="/plans",
                body={
                    "slug": "pyme", "name": "Pyme", "description": "",
                    "monthly_price": 14.99, "annual_price": 143.0,
                    "document_limit": 300, "limit_cycle": "month",
                    "max_locations": 3, "max_emission_points": 5, "max_users": 5,
                    "includes_credit_notes": True, "includes_withholdings": True,
                    "includes_delivery_notes": True, "includes_api": False, "order": 2,
                },
            ), LambdaContext())
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 201)
        self.assertEqual(body["data"]["slug"], "pyme")
        self.assertEqual(len(body["data"]["id"]), 36)        # UUID
        self.assertNotEqual(body["data"]["id"], "pyme")      # PK != slug
        self.assertEqual(self._repo.commit_calls[0]["action"], "CREATE")
        self.assertIs(self._repo.commit_calls[0]["idempotency"], idempotency_context)

    def test_patch_status_uses_uuid(self) -> None:
        mod    = self._load()
        idempotency_context = object()
        with patch.object(mod, "require_current_context", return_value=idempotency_context):
            result = mod.handler(api_event(
                method="PATCH", path="/plans/uuid-basic/status",
                body={"active": False},
            ), LambdaContext())
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertFalse(body["data"]["active"])
        self.assertEqual(body["data"]["slug"], "basic")  # slug untouched
        self.assertEqual(self._repo.commit_calls[0]["action"], "STATUS")

    def test_patch_with_slug_as_id_returns_404(self) -> None:
        mod    = self._load()
        result = mod.handler(api_event(
            method="PATCH", path="/plans/basic/status",   # slug instead of UUID
            body={"active": False},
        ), LambdaContext())
        self.assertEqual(result["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()
