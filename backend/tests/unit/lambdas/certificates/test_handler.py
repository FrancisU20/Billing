from __future__ import annotations

import importlib
import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from shared.errors import OptimisticLockError
from tests.unit.lambdas.certificates.test_use_cases import (
    FakeCertificateStore,
    FakeCertificateValidator,
)
from tests.unit.support import (
    VALID_RUC,
    FakeTenantRepository,
    LambdaContext,
    api_event,
    configure_unit_environment,
    decode_response,
    make_tenant,
)


def _load_handler_module():
    configure_unit_environment()
    os.environ["TENANTS_TABLE"] = "unit-tenants"
    os.environ["AUDIT_LOG_TABLE"] = "unit-audit"
    os.environ.pop("IDEMPOTENCY_TABLE", None)

    sys.modules.pop("lambdas.certificates.handler", None)
    sys.modules.pop("lambdas._base.idempotency", None)
    return importlib.import_module("lambdas.certificates.handler")


def _certificate_event(*, method: str, tenant_id: str, claims: dict | None = None) -> dict:
    return api_event(
        method=method,
        path=f"/tenants/{tenant_id}/certificate",
        path_params={"id": tenant_id},
        body={"certificate_b64": "base64-p12", "cert_password": "secret"}
        if method == "PUT"
        else None,
        headers={"X-Idempotency-Key": "certificate-update-1"} if method == "PUT" else None,
        claims=claims,
    )


_OWNER_CLAIMS = {
    "sub": "user-1",
    "custom:tenant_id": "tenant-1",
    "custom:role": "owner",
    "custom:is_superadmin": "false",
}

_VIEWER_CLAIMS = {
    "sub": "user-2",
    "custom:tenant_id": "tenant-1",
    "custom:role": "viewer",
    "custom:is_superadmin": "false",
}


class CertificatesHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = _load_handler_module()
        self.context = LambdaContext()

    def test_get_returns_certificate_metadata_for_own_tenant(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(
            id="tenant-1",
            cert_subject_ruc=VALID_RUC,
            cert_expires_at=datetime.now(UTC) + timedelta(days=100),
            cert_issuer="Security Data",
            cert_uploaded_at=datetime.now(UTC),
        )
        repo.tenants[tenant.id] = tenant
        event = _certificate_event(method="GET", tenant_id="tenant-1", claims=_OWNER_CLAIMS)

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["cert_subject_ruc"], VALID_RUC)
        self.assertEqual(body["data"]["tenant_id"], "tenant-1")
        self.assertNotIn("certificate_secret_arn", body["data"])

    def test_get_allows_viewer_for_own_tenant(self) -> None:
        repo = FakeTenantRepository()
        repo.tenants["tenant-1"] = make_tenant(id="tenant-1")
        event = _certificate_event(method="GET", tenant_id="tenant-1", claims=_VIEWER_CLAIMS)

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 200)

    def test_get_forbids_cross_tenant_access(self) -> None:
        repo = FakeTenantRepository()
        repo.tenants["tenant-other"] = make_tenant(id="tenant-other")
        event = _certificate_event(method="GET", tenant_id="tenant-other", claims=_OWNER_CLAIMS)

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")

    def test_get_allows_superadmin_for_any_tenant(self) -> None:
        repo = FakeTenantRepository()
        repo.tenants["tenant-other"] = make_tenant(id="tenant-other")
        event = _certificate_event(method="GET", tenant_id="tenant-other")

        with patch.object(self.handler, "_repo", return_value=repo):
            response = self.handler.handler(event, self.context)

        self.assertEqual(response["statusCode"], 200)

    def test_unknown_route_returns_not_found(self) -> None:
        event = api_event(method="DELETE", path="/tenants/tenant-1/certificate")

        response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")

    def test_put_validates_stores_secret_and_commits_with_idempotency(self) -> None:
        repo = FakeTenantRepository()
        repo.tenants["tenant-1"] = make_tenant(id="tenant-1", ruc=VALID_RUC)
        validator = FakeCertificateValidator()
        store = FakeCertificateStore()
        idempotency_context = object()
        event = _certificate_event(method="PUT", tenant_id="tenant-1", claims=_OWNER_CLAIMS)

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "_certificate_validator", return_value=validator),
            patch.object(self.handler, "_certificate_store", return_value=store),
            patch.object(
                self.handler, "require_current_context", return_value=idempotency_context
            ),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["cert_subject_ruc"], VALID_RUC)
        self.assertEqual(len(repo.commit_calls), 1)
        commit = repo.commit_calls[0]
        self.assertEqual(commit["action"], "CERTIFICATE")
        self.assertEqual(commit["events"], [])
        self.assertIs(commit["idempotency"], idempotency_context)
        self.assertEqual(store.put_calls[0]["tenant_id"], "tenant-1")

    def test_put_forbids_cross_tenant_access_before_validating_certificate(self) -> None:
        repo = FakeTenantRepository()
        repo.tenants["tenant-other"] = make_tenant(id="tenant-other")
        validator = FakeCertificateValidator()
        event = _certificate_event(method="PUT", tenant_id="tenant-other", claims=_OWNER_CLAIMS)

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "_certificate_validator", return_value=validator),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 403)
        self.assertEqual(body["error"]["code"], "FORBIDDEN")
        self.assertEqual(validator.calls, [])
        self.assertEqual(repo.commit_calls, [])

    def test_put_retries_commit_on_optimistic_lock_conflict(self) -> None:
        repo = FakeTenantRepository()
        repo.tenants["tenant-1"] = make_tenant(id="tenant-1", ruc=VALID_RUC)
        repo.commit_errors = [OptimisticLockError()]
        validator = FakeCertificateValidator()
        store = FakeCertificateStore()
        event = _certificate_event(method="PUT", tenant_id="tenant-1", claims=_OWNER_CLAIMS)

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "_certificate_validator", return_value=validator),
            patch.object(self.handler, "_certificate_store", return_value=store),
            patch.object(self.handler, "require_current_context", return_value=object()),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        # Reattach re-fetches the tenant once; certificate validation and the
        # secret upload are not repeated.
        self.assertEqual(len(repo.get_by_id_calls), 2)
        self.assertEqual(len(validator.calls), 1)
        self.assertEqual(len(store.put_calls), 1)
        self.assertEqual(len(repo.commit_calls), 2)
        self.assertNotIn("certificate_secret_arn", body["data"])
        self.assertEqual(body["data"]["cert_subject_ruc"], VALID_RUC)

    def test_put_gives_up_after_max_optimistic_lock_conflicts(self) -> None:
        repo = FakeTenantRepository()
        repo.tenants["tenant-1"] = make_tenant(id="tenant-1", ruc=VALID_RUC)
        repo.commit_errors = [OptimisticLockError(), OptimisticLockError(), OptimisticLockError()]
        validator = FakeCertificateValidator()
        store = FakeCertificateStore()
        event = _certificate_event(method="PUT", tenant_id="tenant-1", claims=_OWNER_CLAIMS)

        with (
            patch.object(self.handler, "_repo", return_value=repo),
            patch.object(self.handler, "_certificate_validator", return_value=validator),
            patch.object(self.handler, "_certificate_store", return_value=store),
            patch.object(self.handler, "require_current_context", return_value=object()),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 409)
        self.assertEqual(body["error"]["code"], "OPTIMISTIC_LOCK_ERROR")
        self.assertEqual(len(repo.commit_calls), 3)


if __name__ == "__main__":
    unittest.main()
