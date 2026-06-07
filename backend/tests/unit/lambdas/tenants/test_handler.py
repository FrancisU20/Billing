from __future__ import annotations

import importlib
import os
import sys
import unittest
from unittest.mock import patch

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


def _load_handler_module():
    configure_unit_environment()
    os.environ["TENANTS_TABLE"] = "unit-tenants"
    os.environ["PLANS_TABLE"] = "unit-plans"
    os.environ["AUDIT_LOG_TABLE"] = "unit-audit"
    os.environ["OUTBOX_TABLE"] = ""
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

        with patch.object(self.handler, "_repo", return_value=repo), \
                patch.object(self.handler, "_plan_catalog", return_value=FakePlanCatalog()), \
                patch.object(self.handler, "require_current_context", return_value=idempotency_context):
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

        with patch.object(self.handler, "_repo", return_value=repo), \
                patch.object(self.handler, "require_current_context", return_value=idempotency_context):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 204)
        self.assertEqual(len(repo.commit_calls), 1)
        commit = repo.commit_calls[0]
        self.assertEqual(commit["action"], "DELETE")
        self.assertTrue(commit["tenant"].deleted)
        self.assertEqual(commit["events"][0].event_type, "TenantDeletedEvent")


if __name__ == "__main__":
    unittest.main()
