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
        self._free = Plan(
            id="uuid-free",
            slug="free",
            name="Free",
            monthly_price=Decimal("0.00"),
            document_limit=20,
            limit_cycle="year",
            order=0,
        )
        self._basic = Plan(
            id="uuid-basic",
            slug="basic",
            name="Basic",
            monthly_price=Decimal("5.99"),
            document_limit=50,
            limit_cycle="month",
            order=1,
        )
        self._draft = Plan(
            id="uuid-draft",
            slug="draft",
            name="Draft Plan",
            monthly_price=Decimal("0.00"),
            document_limit=10,
            limit_cycle="month",
            order=99,
            active=False,
        )
        self._by_id = {"uuid-free": self._free, "uuid-basic": self._basic}
        self._by_slug = {"free": self._free, "basic": self._basic, "draft": self._draft}
        self.commit_calls: list[dict[str, Any]] = []
        self.list_calls: list[dict[str, Any]] = []

    def get_by_id(self, plan_id: str) -> Plan:
        if plan_id not in self._by_id:
            raise PlanNotFoundError()
        return self._by_id[plan_id]

    def get_by_slug(self, slug: str) -> Plan:
        if slug not in self._by_slug:
            raise PlanNotFoundError()
        return self._by_slug[slug]

    def save(self, plan: Plan) -> None:
        self._by_id[plan.id] = plan
        self._by_slug[plan.slug] = plan

    def commit(self, **kwargs: Any) -> None:
        self.commit_calls.append(kwargs)
        self.save(kwargs["plan"])

    def list(
        self,
        *,
        status: str | None = None,
        slug: str | None = None,
        q: str | None = None,
        limit_cycle: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> list[Plan]:
        self.list_calls.append(
            {
                "status": status,
                "slug": slug,
                "q": q,
                "limit_cycle": limit_cycle,
                "created_from": created_from,
                "created_to": created_to,
            }
        )
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
        mod = importlib.import_module("lambdas.plans.handler")
        fake_repo = FakePlanRepository()
        mod._repo = lambda: fake_repo
        self._repo = fake_repo
        return mod

    def test_list_public_always_returns_active_only_with_no_filters(self) -> None:
        mod = self._load()
        mod.handler(api_event(method="GET", path="/plans"), LambdaContext())
        self.assertEqual(
            self._repo.list_calls[0],
            {
                "status": "active",
                "slug": None,
                "q": None,
                "limit_cycle": None,
                "created_from": None,
                "created_to": None,
            },
        )

    def test_get_inactive_plan_by_slug_returns_404(self) -> None:
        mod = self._load()
        result = mod.handler(api_event(method="GET", path="/plans/draft"), LambdaContext())
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 404)
        self.assertEqual(body["error"]["code"], "PLAN_NOT_FOUND")

    def test_list_is_public(self) -> None:
        mod = self._load()
        result = mod.handler(api_event(method="GET", path="/plans"), LambdaContext())
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertIn("items", body["data"])
        self.assertEqual(len(body["data"]["items"]), 2)

    def test_list_works_for_anonymous_request_without_jwt(self) -> None:
        # Public pricing: no authorizer claims at all → must not 401
        mod = self._load()
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

    def test_list_ignores_all_query_params(self) -> None:
        mod = self._load()
        mod.handler(
            api_event(
                method="GET",
                path="/plans",
                query={"status": "inactive", "q": "basic", "limit_cycle": "week"},
            ),
            LambdaContext(),
        )
        self.assertEqual(
            self._repo.list_calls[0],
            {
                "status": "active",
                "slug": None,
                "q": None,
                "limit_cycle": None,
                "created_from": None,
                "created_to": None,
            },
        )

    def test_get_by_slug_returns_plan(self) -> None:
        mod = self._load()
        result = mod.handler(api_event(method="GET", path="/plans/free"), LambdaContext())
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(body["data"]["slug"], "free")
        self.assertEqual(body["data"]["id"], "uuid-free")

    def test_get_missing_slug_returns_404(self) -> None:
        mod = self._load()
        result = mod.handler(api_event(method="GET", path="/plans/missing"), LambdaContext())
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 404)
        self.assertEqual(body["error"]["code"], "PLAN_NOT_FOUND")

    def test_create_requires_superadmin(self) -> None:
        mod = self._load()
        event = api_event(
            method="POST",
            path="/plans",
            body={
                "slug": "pro",
                "name": "Pro",
                "document_limit": 1000,
                "monthly_price": 29.99,
                "annual_price": 287.0,
                "limit_cycle": "month",
            },
            claims={
                "sub": "u1",
                "custom:role": "owner",
                "custom:is_superadmin": "false",
                "custom:tenant_id": "t1",
            },
        )
        self.assertEqual(mod.handler(event, LambdaContext())["statusCode"], 403)

    def test_create_superadmin_generates_uuid_as_pk(self) -> None:
        mod = self._load()
        idempotency_context = object()
        with patch.object(mod, "require_current_context", return_value=idempotency_context):
            result = mod.handler(
                api_event(
                    method="POST",
                    path="/plans",
                    body={
                        "slug": "pyme",
                        "name": "Pyme",
                        "description": "",
                        "monthly_price": 14.99,
                        "annual_price": 143.0,
                        "document_limit": 300,
                        "limit_cycle": "month",
                        "max_locations": 3,
                        "max_emission_points": 5,
                        "max_users": 5,
                        "pruebas_monthly_docs_limit": 200,
                        "pruebas_monthly_bulk_limit": 50,
                        "dedicated_queue": False,
                        "self_service": True,
                        "includes_credit_notes": True,
                        "includes_withholdings": True,
                        "includes_delivery_notes": True,
                        "includes_api": False,
                        "order": 2,
                    },
                ),
                LambdaContext(),
            )
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 201)
        self.assertEqual(body["data"]["slug"], "pyme")
        self.assertEqual(len(body["data"]["id"]), 36)  # UUID
        self.assertNotEqual(body["data"]["id"], "pyme")  # PK != slug
        self.assertEqual(self._repo.commit_calls[0]["action"], "CREATE")
        self.assertIs(self._repo.commit_calls[0]["idempotency"], idempotency_context)

    def test_patch_status_uses_uuid(self) -> None:
        mod = self._load()
        idempotency_context = object()
        with patch.object(mod, "require_current_context", return_value=idempotency_context):
            result = mod.handler(
                api_event(
                    method="PATCH",
                    path="/plans/uuid-basic/status",
                    body={"active": False},
                ),
                LambdaContext(),
            )
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertFalse(body["data"]["active"])
        self.assertEqual(body["data"]["slug"], "basic")  # slug untouched
        self.assertEqual(self._repo.commit_calls[0]["action"], "STATUS")

    def test_patch_with_slug_as_id_returns_404(self) -> None:
        mod = self._load()
        result = mod.handler(
            api_event(
                method="PATCH",
                path="/plans/basic/status",  # slug instead of UUID
                body={"active": False},
            ),
            LambdaContext(),
        )
        self.assertEqual(result["statusCode"], 404)

    def test_update_plan_commits_changes(self) -> None:
        mod = self._load()
        idempotency_context = object()
        with patch.object(mod, "require_current_context", return_value=idempotency_context):
            result = mod.handler(
                api_event(
                    method="PATCH",
                    path="/plans/uuid-basic",
                    body={"name": "Basic Actualizado", "monthly_price": 7.99},
                ),
                LambdaContext(),
            )
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(body["data"]["name"], "Basic Actualizado")
        self.assertEqual(self._repo.commit_calls[0]["action"], "UPDATE")
        self.assertIs(self._repo.commit_calls[0]["idempotency"], idempotency_context)

    def test_update_unknown_plan_returns_404(self) -> None:
        mod = self._load()
        idempotency_context = object()
        with patch.object(mod, "require_current_context", return_value=idempotency_context):
            result = mod.handler(
                api_event(
                    method="PATCH",
                    path="/plans/uuid-nonexistent",
                    body={"name": "No importa"},
                ),
                LambdaContext(),
            )
        self.assertEqual(result["statusCode"], 404)

    # ── /superadmin/plans ─────────────────────────────────────────────────────

    def test_admin_list_requires_superadmin(self) -> None:
        mod = self._load()
        result = mod.handler(
            api_event(
                method="GET",
                path="/superadmin/plans",
                claims={
                    "custom:is_superadmin": "false",
                    "custom:role": "owner",
                    "custom:tenant_id": "t1",
                },
            ),
            LambdaContext(),
        )
        self.assertEqual(result["statusCode"], 403)

    def test_admin_list_returns_items(self) -> None:
        mod = self._load()
        result = mod.handler(api_event(method="GET", path="/superadmin/plans"), LambdaContext())
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertIn("items", body["data"])

    def test_admin_list_passes_inactive_status_to_repo(self) -> None:
        mod = self._load()
        mod.handler(
            api_event(method="GET", path="/superadmin/plans", query={"status": "inactive"}),
            LambdaContext(),
        )
        self.assertEqual(self._repo.list_calls[0]["status"], "inactive")

    def test_admin_list_without_status_filter_sends_none_to_repo(self) -> None:
        mod = self._load()
        mod.handler(api_event(method="GET", path="/superadmin/plans"), LambdaContext())
        self.assertIsNone(self._repo.list_calls[0]["status"])

    def test_admin_get_returns_active_plan(self) -> None:
        mod = self._load()
        result = mod.handler(
            api_event(method="GET", path="/superadmin/plans/free", path_params={"id": "free"}),
            LambdaContext(),
        )
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(body["data"]["slug"], "free")

    def test_admin_get_returns_inactive_plan(self) -> None:
        mod = self._load()
        result = mod.handler(
            api_event(method="GET", path="/superadmin/plans/draft", path_params={"id": "draft"}),
            LambdaContext(),
        )
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(body["data"]["slug"], "draft")
        self.assertFalse(body["data"]["active"])

    def test_admin_get_requires_superadmin(self) -> None:
        mod = self._load()
        result = mod.handler(
            api_event(
                method="GET",
                path="/superadmin/plans/free",
                path_params={"id": "free"},
                claims={
                    "custom:is_superadmin": "false",
                    "custom:role": "owner",
                    "custom:tenant_id": "t1",
                },
            ),
            LambdaContext(),
        )
        self.assertEqual(result["statusCode"], 403)


if __name__ == "__main__":
    unittest.main()
