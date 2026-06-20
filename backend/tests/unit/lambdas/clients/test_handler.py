from __future__ import annotations

import importlib
import os
import sys
import unittest
from unittest.mock import patch

from lambdas.clients.domain.errors import ClientDuplicateIdentificationError
from tests.unit.support import (
    FakeClientRepository,
    LambdaContext,
    api_event,
    client_payload,
    configure_unit_environment,
    decode_response,
    make_client,
)


def _tenant_claims(role: str = "admin") -> dict[str, str]:
    return {
        "sub": "user-1",
        "custom:is_superadmin": "false",
        "custom:tenant_id": "tenant-1",
        "custom:role": role,
    }


def _load_handler_module():
    configure_unit_environment()
    os.environ["CLIENTS_TABLE"] = "unit-clients"
    os.environ["AUDIT_LOG_TABLE"] = ""
    os.environ.pop("IDEMPOTENCY_TABLE", None)
    sys.modules.pop("lambdas.clients.handler", None)
    sys.modules.pop("lambdas._base.idempotency", None)
    return importlib.import_module("lambdas.clients.handler")


class ClientsHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = _load_handler_module()
        self.context = LambdaContext()

    def test_create_commits_client_with_idempotency_context(self) -> None:
        repo = FakeClientRepository()
        idempotency_context = object()
        event = api_event(
            method="POST",
            path="/clients",
            body=client_payload(),
            headers={"X-Idempotency-Key": "create-client-1"},
            claims=_tenant_claims("admin"),
        )

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["tenant_id"], "tenant-1")
        self.assertEqual(len(repo.commit_calls), 1)
        self.assertEqual(repo.commit_calls[0]["action"], "CREATE")
        self.assertIs(repo.commit_calls[0]["idempotency"], idempotency_context)

    def test_viewer_can_list_clients(self) -> None:
        repo = FakeClientRepository()
        repo.list_result = ([make_client(id="client-1")], None)
        event = api_event(
            method="GET",
            path="/clients",
            query={"limit": "10"},
            claims=_tenant_claims("viewer"),
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(len(body["data"]["items"]), 1)

    def test_list_includes_total_when_no_text_filter_is_active(self) -> None:
        repo = FakeClientRepository()
        repo.list_result = ([make_client(id="client-1")], None)
        repo.count_result = 5
        event = api_event(
            method="GET",
            path="/clients",
            query={"status": "active"},
            claims=_tenant_claims("admin"),
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(body["data"]["total"], 5)

    def test_list_omits_total_when_q_filter_is_active(self) -> None:
        repo = FakeClientRepository()
        repo.list_result = ([make_client(id="client-1")], None)
        repo.count_result = 5
        event = api_event(
            method="GET",
            path="/clients",
            query={"q": "acme"},
            claims=_tenant_claims("admin"),
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertNotIn("total", body["data"])

    def test_list_passes_exact_identification_filter(self) -> None:
        repo = FakeClientRepository()
        repo.list_result = ([make_client(id="client-1")], None)
        event = api_event(
            method="GET",
            path="/clients",
            query={"identification": "1792146739001"},
            claims=_tenant_claims("admin"),
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(repo.list_calls[0]["identification"], "1792146739001")

    def test_list_passes_type_and_created_at_filters(self) -> None:
        repo = FakeClientRepository()
        repo.list_result = ([make_client(id="client-1")], None)
        event = api_event(
            method="GET",
            path="/clients",
            query={
                "identification_type": "ruc",
                "created_from": "2026-06-01",
                "created_to": "2026-06-08",
            },
            claims=_tenant_claims("admin"),
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(repo.list_calls[0]["identification_type"], "ruc")
        self.assertEqual(repo.list_calls[0]["created_from"], "2026-06-01T05:00:00+00:00")
        self.assertEqual(repo.list_calls[0]["created_to"], "2026-06-09T04:59:59.999999+00:00")

    def test_list_rejects_invalid_identification_type(self) -> None:
        event = api_event(
            method="GET",
            path="/clients",
            query={"identification_type": "foreign"},
            claims=_tenant_claims("admin"),
        )

        response = self.handler.handler(event, self.context)
        body = decode_response(response)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")

    def test_list_rejects_invalid_status(self) -> None:
        event = api_event(
            method="GET",
            path="/clients",
            query={"status": "blocked"},
            claims=_tenant_claims("admin"),
        )

        response = self.handler.handler(event, self.context)
        body = decode_response(response)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")

    def test_viewer_cannot_create_client(self) -> None:
        repo = FakeClientRepository()
        event = api_event(
            method="POST",
            path="/clients",
            body=client_payload(),
            claims=_tenant_claims("viewer"),
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertEqual(repo.commit_calls, [])

    def test_viewer_cannot_update_client(self) -> None:
        repo = FakeClientRepository()
        event = api_event(
            method="PATCH",
            path="/clients/client-1",
            body={"trade_name": "No permitido"},
            claims=_tenant_claims("viewer"),
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertEqual(repo.commit_calls, [])

    def test_viewer_cannot_delete_client(self) -> None:
        repo = FakeClientRepository()
        event = api_event(
            method="DELETE",
            path="/clients/client-1",
            claims=_tenant_claims("viewer"),
        )

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertEqual(repo.commit_calls, [])

    def test_get_returns_client_by_id(self) -> None:
        repo = FakeClientRepository()
        client = make_client(id="client-1")
        repo.clients[client.id] = client
        event = api_event(method="GET", path="/clients/client-1", claims=_tenant_claims("viewer"))

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["id"], "client-1")

    def test_update_commits_changes(self) -> None:
        repo = FakeClientRepository()
        client = make_client(id="client-1")
        repo.clients[client.id] = client
        idempotency_context = object()
        event = api_event(
            method="PATCH",
            path="/clients/client-1",
            body={"trade_name": "Actualizado"},
            headers={"X-Idempotency-Key": "update-client-1"},
            claims=_tenant_claims("owner"),
        )

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(repo.commit_calls[0]["action"], "UPDATE")
        self.assertEqual(repo.commit_calls[0]["client"].trade_name, "Actualizado")

    def test_create_duplicate_from_commit_returns_409(self) -> None:
        repo = FakeClientRepository()
        repo.commit_error = ClientDuplicateIdentificationError()
        idempotency_context = object()
        event = api_event(
            method="POST",
            path="/clients",
            body=client_payload(),
            headers={"X-Idempotency-Key": "duplicate-client-1"},
            claims=_tenant_claims("admin"),
        )

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 409)
        self.assertEqual(body["error"]["code"], "CLIENT_DUPLICATE_IDENTIFICATION")

    def test_delete_commits_soft_deleted_client(self) -> None:
        repo = FakeClientRepository()
        client = make_client(id="client-1")
        repo.clients[client.id] = client
        idempotency_context = object()
        event = api_event(
            method="DELETE",
            path="/clients/client-1",
            headers={"X-Idempotency-Key": "delete-client-1"},
            claims=_tenant_claims("admin"),
        )

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 204)
        self.assertTrue(repo.commit_calls[0]["client"].deleted)

    def test_superadmin_without_tenant_context_is_rejected(self) -> None:
        event = api_event(method="GET", path="/clients")

        response = self.handler.handler(event, self.context)
        body = decode_response(response)

        self.assertEqual(response["statusCode"], 401)
        self.assertEqual(body["error"]["code"], "MISSING_TENANT_CONTEXT")


if __name__ == "__main__":
    unittest.main()
