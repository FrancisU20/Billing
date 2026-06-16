from __future__ import annotations

import importlib
import os
import sys
import unittest
from unittest.mock import patch

from lambdas.tenants.domain.repositories.i_payment_reader import IPaymentReader, PaymentRecord
from tests.unit.support import (
    FakePlanCatalog,
    FakeTenantRepository,
    LambdaContext,
    api_event,
    configure_unit_environment,
    decode_response,
    make_tenant,
    tenant_payload,
)


class FakePaymentReader(IPaymentReader):
    def __init__(self, *, payment: PaymentRecord | None = None) -> None:
        self._payment = payment

    def get_by_order_id(self, order_id: str) -> PaymentRecord:
        from lambdas.tenants.domain.errors import SubscriptionRenewalPaymentNotFoundError

        if self._payment is None:
            raise SubscriptionRenewalPaymentNotFoundError()
        return self._payment

    def mark_applied_to_tenant(self, order_id: str, tenant_id: str) -> dict:
        return {"ConditionCheck": {"TableName": "payments", "Key": {"id": f"PAYMENT#{order_id}"}}}


def _captured_payment(plan_id: str = "uuid-basic") -> PaymentRecord:
    return PaymentRecord(
        order_id="ORD-1",
        tenant_id="",
        plan_id=plan_id,
        amount="5.99",
        status="CAPTURED",
        plan_cycle="month",
        payer_id="PAY-1",
    )


def _load_handler_module():
    configure_unit_environment()
    os.environ["TENANTS_TABLE"] = "unit-tenants"
    os.environ["PLANS_TABLE"] = "unit-plans"
    os.environ["AUDIT_LOG_TABLE"] = "unit-audit"
    os.environ["OUTBOX_TABLE"] = ""
    os.environ["PAYMENTS_TABLE"] = "unit-payments"
    os.environ.pop("IDEMPOTENCY_TABLE", None)

    sys.modules.pop("lambdas.tenants.handler", None)
    sys.modules.pop("lambdas._base.idempotency", None)
    return importlib.import_module("lambdas.tenants.handler")


class TenantsHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = _load_handler_module()
        self.context = LambdaContext()

    def test_create_commits_tenant_with_event_and_idempotency_context(self) -> None:
        repo = FakeTenantRepository()
        idempotency_context = object()
        event = api_event(
            method="POST",
            path="/tenants",
            body=tenant_payload(),
            headers={"X-Idempotency-Key": "create-tenant-1"},
        )

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "_plan_catalog", return_value=FakePlanCatalog()),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue(body["success"])
        self.assertEqual(len(repo.commit_calls), 1)
        commit = repo.commit_calls[0]
        self.assertEqual(commit["action"], "CREATE")
        self.assertIs(commit["idempotency"], idempotency_context)
        self.assertEqual(commit["response"]["statusCode"], 201)
        self.assertEqual(commit["events"][0].event_type, "TenantCreatedEvent")

    def test_update_forbids_cross_tenant_access_before_touching_repository(self) -> None:
        repo = FakeTenantRepository()
        event = api_event(
            method="PATCH",
            path="/tenants/tenant-b",
            body={"trade_name": "Not allowed"},
            claims={
                "custom:is_superadmin": "false",
                "custom:tenant_id": "tenant-a",
                "custom:role": "admin",
            },
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertEqual(repo.commit_calls, [])

    def test_list_returns_paginated_response(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="t-1")
        repo.list_result = ([tenant], None)
        event = api_event(method="GET", path="/tenants", query={"limit": "10"})

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(body["success"])
        self.assertIn("items", body["data"])
        self.assertEqual(len(body["data"]["items"]), 1)

    def test_list_passes_search_and_filter_query(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="t-1")
        repo.list_result = ([tenant], None)
        event = api_event(
            method="GET",
            path="/tenants",
            query={
                "q": "codelabs",
                "ruc": "1792146739001",
                "status": "active",
                "sri_environment": "testing",
                "plan_status": "active",
                "created_from": "2026-06-01",
                "created_to": "2026-06-08",
            },
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 200)
        call = repo.list_calls[0]
        self.assertEqual(call["q"], "codelabs")
        self.assertEqual(call["ruc"], "1792146739001")
        self.assertEqual(call["status"], "active")
        self.assertEqual(call["sri_environment"], "testing")
        self.assertEqual(call["plan_status"], "active")
        self.assertEqual(call["created_from"], "2026-06-01T00:00:00+00:00")
        self.assertEqual(call["created_to"], "2026-06-08T23:59:59.999999+00:00")

    def test_list_rejects_invalid_plan_status(self) -> None:
        event = api_event(method="GET", path="/tenants", query={"plan_status": "paused"})

        response = self.handler.handler(event, self.context)
        body = decode_response(response)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")

    def test_get_returns_tenant_by_id(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="t-get-1")
        repo.tenants[tenant.id] = tenant
        event = api_event(method="GET", path="/tenants/t-get-1")

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["id"], "t-get-1")

    def test_get_unknown_tenant_returns_404(self) -> None:
        repo = FakeTenantRepository()
        event = api_event(method="GET", path="/tenants/does-not-exist")

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 404)
        self.assertEqual(body["error"]["code"], "TENANT_NOT_FOUND")

    def test_update_commits_changes(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="t-upd-1")
        repo.tenants[tenant.id] = tenant
        idempotency_context = object()
        event = api_event(
            method="PATCH",
            path="/tenants/t-upd-1",
            body={"trade_name": "Nuevo Nombre"},
            headers={"X-Idempotency-Key": "upd-1"},
        )

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(len(repo.commit_calls), 1)
        self.assertEqual(repo.commit_calls[0]["action"], "UPDATE")
        self.assertEqual(repo.commit_calls[0]["tenant"].trade_name, "Nuevo Nombre")

    def test_toggle_status_commits_status_change(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="t-tog-1")
        repo.tenants[tenant.id] = tenant
        idempotency_context = object()
        event = api_event(
            method="PATCH",
            path="/tenants/t-tog-1/status",
            body={"status": "suspended"},
            headers={"X-Idempotency-Key": "tog-1"},
        )

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(repo.commit_calls[0]["action"], "STATUS")
        self.assertEqual(repo.commit_calls[0]["tenant"].status.value, "suspended")

    def test_retry_onboarding_enqueues_tenant_created_event_without_mutating_tenant(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-retry-1", email="owner@codelabs.com")
        repo.tenants[tenant.id] = tenant
        idempotency_context = object()
        event = api_event(
            method="POST",
            path="/tenants/tenant-retry-1/onboarding/retry",
            headers={"X-Idempotency-Key": "retry-onboarding-1"},
        )

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["status"], "queued")
        self.assertEqual(repo.commit_calls, [])
        self.assertEqual(len(repo.commit_admin_events_calls), 1)
        commit = repo.commit_admin_events_calls[0]
        self.assertEqual(commit["action"], "ONBOARDING_RETRY")
        self.assertIs(commit["idempotency"], idempotency_context)
        self.assertEqual(commit["events"][0].event_type, "TenantCreatedEvent")
        self.assertEqual(commit["events"][0].tenant_id, "tenant-retry-1")
        self.assertEqual(commit["tenant"].version, tenant.version)

    def test_retry_onboarding_on_completed_inactive_tenant_still_enqueues_event(self) -> None:
        """Documents current behavior: retry has no guard on tenant.status or
        onboarding_completed_at. It always re-enqueues TenantCreatedEvent without
        mutating the tenant. This is safe because:
        - the endpoint is superadmin-only (recovery tool, not self-service);
        - the worker `tenant_onboarding` is idempotent: AdminCreateUser/reset of the
          temporary password is a no-op once the Cognito user has completed its own
          NEW_PASSWORD_REQUIRED challenge.
        If this ever needs to become a guarded operation (e.g. confirm before resending
        credentials to an already-active owner), this test should be updated to assert
        the new behavior."""
        from lambdas.tenants.domain.enums import TenantStatus

        repo = FakeTenantRepository()
        tenant = make_tenant(
            id="tenant-retry-2",
            email="owner@codelabs.com",
            status=TenantStatus.INACTIVE,
            onboarding_completed_at="2026-01-01T00:00:00+00:00",
        )
        repo.tenants[tenant.id] = tenant
        idempotency_context = object()
        event = api_event(
            method="POST",
            path="/tenants/tenant-retry-2/onboarding/retry",
            headers={"X-Idempotency-Key": "retry-onboarding-2"},
        )

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["status"], "queued")
        self.assertEqual(repo.commit_calls, [])
        self.assertEqual(len(repo.commit_admin_events_calls), 1)
        commit = repo.commit_admin_events_calls[0]
        self.assertEqual(commit["tenant"].status, TenantStatus.INACTIVE)
        self.assertEqual(commit["tenant"].onboarding_completed_at, "2026-01-01T00:00:00+00:00")

    def test_retry_onboarding_requires_superadmin(self) -> None:
        repo = FakeTenantRepository()
        event = api_event(
            method="POST",
            path="/tenants/tenant-retry-1/onboarding/retry",
            headers={"X-Idempotency-Key": "retry-onboarding-1"},
            claims={
                "custom:is_superadmin": "false",
                "custom:tenant_id": "tenant-retry-1",
                "custom:role": "owner",
            },
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertEqual(repo.commit_admin_events_calls, [])

    def test_delete_commits_soft_deleted_tenant(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant
        idempotency_context = object()
        event = api_event(
            method="DELETE",
            path="/tenants/tenant-1",
            headers={"X-Idempotency-Key": "delete-tenant-1"},
        )

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 204)
        self.assertEqual(len(repo.commit_calls), 1)
        commit = repo.commit_calls[0]
        self.assertEqual(commit["action"], "DELETE")
        self.assertTrue(commit["tenant"].deleted)
        self.assertEqual(commit["events"], [])


class SubscriptionRenewalHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = _load_handler_module()
        self.context = LambdaContext()

    def _call(self, tenant_id: str, body: dict, repo=None, reader=None, claims=None) -> dict:
        _repo = repo or FakeTenantRepository()
        _reader = reader or FakePaymentReader()
        idempotency_context = object()
        event = api_event(
            method="POST",
            path=f"/tenants/{tenant_id}/subscription/renew",
            path_params={"id": tenant_id},
            body=body,
            headers={"X-Idempotency-Key": "renew-1"},
            claims=claims,
        )
        with (
            patch.object(self.handler, "_repo", return_value=_repo),
            patch.object(self.handler, "_payment_reader", return_value=_reader),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            return self.handler.handler(event, self.context)

    def test_returns_200_with_renewal_data(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant
        reader = FakePaymentReader(payment=_captured_payment(plan_id=tenant.plan_id))

        resp = self._call("tenant-1", {"order_id": "ORD-1"}, repo=repo, reader=reader)
        self.assertEqual(resp["statusCode"], 200)
        body = decode_response(resp)
        self.assertEqual(body["data"]["tenant_id"], "tenant-1")
        self.assertEqual(body["data"]["subscription_status"], "active")
        self.assertIn("plan_cycle_ends_at", body["data"])

    def test_commit_includes_payment_transact_item(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant
        reader = FakePaymentReader(payment=_captured_payment(plan_id=tenant.plan_id))

        self._call("tenant-1", {"order_id": "ORD-1"}, repo=repo, reader=reader)

        self.assertEqual(len(repo.commit_calls), 1)
        commit = repo.commit_calls[0]
        self.assertEqual(commit["action"], "SUBSCRIPTION_RENEWAL")
        extra = commit.get("extra_transact_items", [])
        self.assertEqual(len(extra), 1)
        self.assertIn("ConditionCheck", extra[0])

    def test_forbids_cross_tenant_access(self) -> None:
        resp = self._call(
            "other-tenant",
            {"order_id": "ORD-1"},
            claims={
                "custom:is_superadmin": "false",
                "custom:tenant_id": "tenant-1",
                "custom:role": "owner",
            },
        )
        self.assertEqual(resp["statusCode"], 403)

    def test_superadmin_can_renew_any_tenant(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-x")
        repo.tenants[tenant.id] = tenant
        reader = FakePaymentReader(payment=_captured_payment(plan_id=tenant.plan_id))

        resp = self._call(
            "tenant-x",
            {"order_id": "ORD-1"},
            repo=repo,
            reader=reader,
            claims={"custom:is_superadmin": "true", "custom:tenant_id": ""},
        )
        self.assertEqual(resp["statusCode"], 200)

    def test_returns_404_if_payment_not_found(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant

        resp = self._call("tenant-1", {"order_id": "MISSING"}, repo=repo)
        self.assertEqual(resp["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()
