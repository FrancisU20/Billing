from __future__ import annotations

import importlib
import os
import sys
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from lambdas.documents.domain.entities import Document, DocumentStatus
from lambdas.documents.infra.plan_reader import PlanInfo
from lambdas.tenants.domain.enums import SriEnvironment
from shared.errors import ValidationError
from tests.unit.lambdas.documents.test_use_cases import FakeDocumentsRepository, FakeSequencesPort
from tests.unit.support import LambdaContext, api_event, configure_unit_environment, decode_response

_CTX = LambdaContext()
_FAKE_IDEMPOTENCY = object()
_TODAY = date(2026, 6, 17)


def _load_handler():
    configure_unit_environment()
    os.environ["DOCUMENTS_TABLE"] = "unit-documents"
    os.environ["SEQUENCES_TABLE"] = "unit-sequences"
    os.environ["TENANTS_TABLE"] = "unit-tenants"
    os.environ["PLANS_TABLE"] = "unit-plans"
    os.environ["SIGN_QUEUE_URL"] = ""
    os.environ["DOCUMENTS_BUCKET"] = "unit-bucket"
    os.environ.pop("IDEMPOTENCY_TABLE", None)
    for mod in list(sys.modules):
        if mod.startswith("lambdas.documents.handler") or mod == "lambdas._base.idempotency":
            sys.modules.pop(mod, None)
    return importlib.import_module("lambdas.documents.handler")


def _owner_claims(tenant_id: str = "t-1") -> dict:
    return {
        "custom:tenant_id": tenant_id,
        "custom:role": "owner",
        "custom:is_superadmin": "false",
        "sub": "user-1",
    }


def _fake_tenant(tenant_id: str = "t-1") -> MagicMock:
    t = MagicMock()
    t.ruc = "1790000000001"
    t.sri_environment = SriEnvironment.TESTING
    t.certificate_secret_arn = "arn:aws:secretsmanager:us-east-1:1234:secret:cert"
    t.plan_id = "plan-1"
    return t


def _fake_plan() -> PlanInfo:
    return PlanInfo(document_limit=-1, pruebas_monthly_docs_limit=-1)


def _emit_body(**overrides) -> dict:
    base = {
        "establishment_code": "001",
        "emission_point_code": "001",
        "doc_type": "01",
        "issued_at": _TODAY.isoformat(),
        "buyer_id_type": "07",
        "buyer_id": "9999999999999",
        "buyer_name": "Consumidor Final",
        "payment_method": "01",
        "lines": [
            {
                "code": "P001",
                "description": "Producto Test",
                "quantity": "1",
                "unit_price": "10.00",
                "discount": "0.00",
                "iva_rate": "15",
            }
        ],
    }
    base.update(overrides)
    return base


def _make_saved_document() -> Document:
    return Document(
        document_id="doc-1",
        tenant_id="t-1",
        doc_type="01",
        status=DocumentStatus.PENDING,
        serie="001001",
        sequential=1,
        access_key="1" * 49,
        client_id=None,
        buyer_id_type="07",
        buyer_id="9999999999999",
        buyer_name="Consumidor Final",
        buyer_email=None,
        issued_at=_TODAY,
        sri_environment="testing",
        subtotal=Decimal("10.00"),
        total_discount=Decimal("0.00"),
        iva_15=Decimal("1.50"),
        iva_5=Decimal("0.00"),
        iva_0=Decimal("0.00"),
        total=Decimal("11.50"),
        payment_method="01",
        lines=[],
    )


# ── POST /documents (emit) ────────────────────────────────────────────────────


class EmitDocumentHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_handler()

    def _run(self, body: dict | None = None, claims: dict | None = None) -> dict:
        repo = FakeDocumentsRepository()
        seq = FakeSequencesPort()
        tenant = _fake_tenant()
        plan = _fake_plan()
        event = api_event(
            method="POST",
            path="/documents",
            body=body or _emit_body(),
            claims=claims or _owner_claims(),
            headers={"x-idempotency-key": "idem-1"},
        )
        with (
            patch.object(self.mod, "_repo", return_value=repo),
            patch.object(self.mod, "_sequences_port", return_value=seq),
            patch.object(self.mod, "_get_tenant", return_value=tenant),
            patch.object(self.mod, "_get_plan", return_value=plan),
            patch.object(self.mod, "_send_sign_message"),
            patch.object(self.mod, "require_current_context", return_value=_FAKE_IDEMPOTENCY),
        ):
            return self.mod.handler(event, _CTX)

    def test_returns_202(self) -> None:
        resp = self._run()
        self.assertEqual(resp["statusCode"], 202)

    def test_response_contains_document_id_and_access_key(self) -> None:
        resp = self._run()
        body = decode_response(resp)
        self.assertIn("document_id", body["data"])
        self.assertIn("access_key", body["data"])
        self.assertIn("sequential", body["data"])

    def test_requires_owner_or_admin_role(self) -> None:
        resp = self._run(
            claims={
                "custom:tenant_id": "t-1",
                "custom:role": "viewer",
                "custom:is_superadmin": "false",
                "sub": "user-1",
            }
        )
        self.assertEqual(resp["statusCode"], 403)

    def test_invalid_body_returns_400(self) -> None:
        resp = self._run(body={"establishment_code": "001"})
        self.assertEqual(resp["statusCode"], 400)


# ── GET /documents ────────────────────────────────────────────────────────────


class ListDocumentsHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_handler()

    def test_returns_200_with_empty_list(self) -> None:
        repo = FakeDocumentsRepository()
        event = api_event(
            method="GET",
            path="/documents",
            claims=_owner_claims("t-1"),
        )
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(event, _CTX)
        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(body["data"]["items"], [])

    def test_includes_total_from_repository_count(self) -> None:
        repo = FakeDocumentsRepository()
        repo.count_result = 8
        event = api_event(
            method="GET",
            path="/documents",
            claims=_owner_claims("t-1"),
        )
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(event, _CTX)
        body = decode_response(resp)
        self.assertEqual(body["data"]["total"], 8)

    def test_passes_general_search_query_to_repository(self) -> None:
        repo = FakeDocumentsRepository()
        event = api_event(
            method="GET",
            path="/documents",
            query={"q": "Ulloa"},
            claims=_owner_claims("t-1"),
        )
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(event, _CTX)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(repo.list_calls[0]["q"], "Ulloa")
        self.assertEqual(repo.count_calls[0]["q"], "Ulloa")

    def test_superadmin_can_pass_tenant_id_via_query(self) -> None:
        repo = FakeDocumentsRepository()
        repo.seed(_make_saved_document())
        event = api_event(
            method="GET",
            path="/documents",
            query={"tenant_id": "t-1"},
        )
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(event, _CTX)
        self.assertEqual(resp["statusCode"], 200)


# ── GET /documents/summary ────────────────────────────────────────────────────


class DocumentsSummaryHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_handler()

    def test_returns_month_summary_with_plan_limit(self) -> None:
        repo = FakeDocumentsRepository()
        repo.summary_result = repo.summary_result.__class__(
            period_start="2026-06-01",
            period_end="2026-06-17",
            issued_count=4,
            authorized_count=2,
            rejected_count=1,
            failed_count=1,
            pending_count=0,
            processing_count=0,
            authorized_total=Decimal("99.90"),
        )
        event = api_event(
            method="GET",
            path="/documents/summary",
            claims=_owner_claims("t-1"),
        )

        with (
            patch.object(self.mod, "_repo", return_value=repo),
            patch.object(self.mod, "_get_tenant", return_value=_fake_tenant()),
            patch.object(
                self.mod,
                "_get_plan",
                return_value=PlanInfo(document_limit=500, pruebas_monthly_docs_limit=50),
            ),
        ):
            resp = self.mod.handler(event, _CTX)

        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(body["data"]["issued_count"], 4)
        self.assertEqual(body["data"]["authorized_total"], "99.90")
        self.assertEqual(body["data"]["document_limit"], 50)
        self.assertFalse(body["data"]["is_unlimited"])

    def test_returns_unlimited_when_plan_has_sentinel_limit(self) -> None:
        repo = FakeDocumentsRepository()
        event = api_event(
            method="GET",
            path="/documents/summary",
            claims=_owner_claims("t-1"),
        )

        with (
            patch.object(self.mod, "_repo", return_value=repo),
            patch.object(self.mod, "_get_tenant", return_value=_fake_tenant()),
            patch.object(self.mod, "_get_plan", return_value=_fake_plan()),
        ):
            resp = self.mod.handler(event, _CTX)

        body = decode_response(resp)
        self.assertTrue(body["data"]["is_unlimited"])

    def test_omits_limit_when_plan_cannot_be_resolved(self) -> None:
        repo = FakeDocumentsRepository()
        event = api_event(
            method="GET",
            path="/documents/summary",
            claims=_owner_claims("t-1"),
        )

        with (
            patch.object(self.mod, "_repo", return_value=repo),
            patch.object(self.mod, "_get_tenant", return_value=_fake_tenant()),
            patch.object(
                self.mod, "_get_plan", side_effect=ValidationError("plan_id inválido o inactivo")
            ),
        ):
            resp = self.mod.handler(event, _CTX)

        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 200)
        self.assertIsNone(body["data"]["document_limit"])
        self.assertFalse(body["data"]["is_unlimited"])


# ── GET /documents/{id} ───────────────────────────────────────────────────────


class GetDocumentHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_handler()

    def test_returns_200_with_document(self) -> None:
        repo = FakeDocumentsRepository()
        repo.seed(_make_saved_document())
        event = api_event(
            method="GET",
            path="/documents/doc-1",
            claims=_owner_claims("t-1"),
            path_params={"id": "doc-1"},
        )
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(event, _CTX)
        self.assertEqual(resp["statusCode"], 200)
        body = decode_response(resp)
        self.assertEqual(body["data"]["document_id"], "doc-1")

    def test_returns_404_when_not_found(self) -> None:
        repo = FakeDocumentsRepository()
        event = api_event(
            method="GET",
            path="/documents/missing",
            claims=_owner_claims("t-1"),
            path_params={"id": "missing"},
        )
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(event, _CTX)
        self.assertEqual(resp["statusCode"], 404)


# ── GET /documents/{id}/ride ──────────────────────────────────────────────────


class GetRideUrlHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_handler()

    def test_returns_presigned_url(self) -> None:
        repo = FakeDocumentsRepository()
        doc = _make_saved_document()
        doc.status = DocumentStatus.AUTHORIZED
        doc.ride_s3_key = "tenants/t-1/docs/2026/doc-1.pdf"
        repo.seed(doc)
        event = api_event(
            method="GET",
            path="/documents/doc-1/ride",
            claims=_owner_claims("t-1"),
            path_params={"id": "doc-1"},
        )
        with (
            patch.object(self.mod, "_repo", return_value=repo),
            patch("lambdas.documents.use_cases.get_ride_url.boto3") as mock_boto3,
        ):
            mock_boto3.client.return_value.generate_presigned_url.return_value = "https://presigned"
            resp = self.mod.handler(event, _CTX)
        self.assertEqual(resp["statusCode"], 200)
        body = decode_response(resp)
        self.assertEqual(body["data"]["url"], "https://presigned")

    def test_returns_422_if_not_authorized(self) -> None:
        repo = FakeDocumentsRepository()
        repo.seed(_make_saved_document())
        event = api_event(
            method="GET",
            path="/documents/doc-1/ride",
            claims=_owner_claims("t-1"),
            path_params={"id": "doc-1"},
        )
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(event, _CTX)
        self.assertEqual(resp["statusCode"], 422)
