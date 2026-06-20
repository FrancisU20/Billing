from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from lambdas.documents.domain.commands import (
    EmitDocumentCommand,
    GetDocumentCommand,
    LineData,
    ListDocumentsCommand,
)
from lambdas.documents.domain.entities import Document, DocumentStatus
from lambdas.documents.domain.errors import (
    CertificateNotUploadedError,
    DocumentLimitReachedError,
    DocumentNotFoundError,
    InvalidIssuedDateError,
    RideNotAvailableError,
)
from lambdas.documents.domain.repositories.i_discount_campaign_port import (
    DiscountCampaignSnapshot,
)
from lambdas.documents.domain.repositories.i_product_catalog import InvoiceProductSnapshot
from lambdas.documents.use_cases.emit_document import EmitDocumentUseCase
from lambdas.documents.use_cases.get_document import GetDocumentUseCase
from lambdas.documents.use_cases.get_ride_url import GetRideUrlUseCase
from lambdas.documents.use_cases.list_documents import ListDocumentsUseCase
from shared.errors import ValidationError
from tests.unit.support import configure_unit_environment

configure_unit_environment()

_TODAY = date(2026, 6, 17)

# ── Fake repository / port ────────────────────────────────────────────────────


class FakeDocumentsRepository:
    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}
        self.save_calls: list[Document] = []
        self._month_count: int = 0
        self.count_result: int = 0
        self.count_calls: list[dict[str, Any]] = []

    def get(self, tenant_id: str, document_id: str) -> Document:
        doc = self.documents.get(f"{tenant_id}#{document_id}")
        if doc is None:
            raise DocumentNotFoundError()
        return doc

    def list(
        self,
        tenant_id: str,
        **kwargs: Any,
    ) -> tuple[list[Document], str | None]:
        docs = [d for d in self.documents.values() if d.tenant_id == tenant_id]
        return docs, None

    def count_this_month(self, tenant_id: str, sri_environment: str) -> int:
        return self._month_count

    def count(self, tenant_id: str, **kwargs: Any) -> int:
        self.count_calls.append({"tenant_id": tenant_id, **kwargs})
        return self.count_result

    def save(self, document: Document, **kwargs: Any) -> None:
        self.save_calls.append(document)
        self.documents[f"{document.tenant_id}#{document.document_id}"] = document

    def seed(self, document: Document) -> None:
        self.documents[f"{document.tenant_id}#{document.document_id}"] = document

    def set_month_count(self, count: int) -> None:
        self._month_count = count


class FakeSequencesPort:
    def __init__(self, next_value: int = 1) -> None:
        self._next = next_value

    def reserve_next(self, tenant_id: str, serie: str) -> int:
        val = self._next
        self._next += 1
        return val


class FakeProductCatalog:
    def __init__(self) -> None:
        self.snapshots = {
            "prod-1": InvoiceProductSnapshot(
                product_id="prod-1",
                code="SKU-001",
                description="Servicio desde catálogo",
                unit_price=Decimal("30.00"),
                iva_rate="5",
            ),
            "prod-2": InvoiceProductSnapshot(
                product_id="prod-2",
                code="SKU-002",
                description="Producto con descuento propio",
                unit_price=Decimal("30.00"),
                iva_rate="15",
                discount_percentage=Decimal("60.00"),
            ),
        }

    def get_active_snapshot(self, product_id: str) -> InvoiceProductSnapshot:
        return self.snapshots[product_id]


class FakeDiscountCampaignPort:
    def __init__(self, *, active: bool = False, percentage: Decimal = Decimal("0")) -> None:
        self._snapshot = DiscountCampaignSnapshot(active=active, percentage=percentage)

    def get_active_campaign(self) -> DiscountCampaignSnapshot:
        return self._snapshot


def _make_emit_cmd(**overrides: Any) -> EmitDocumentCommand:
    defaults: dict[str, Any] = {
        "tenant_id": "t-1",
        "ruc": "1790000000001",
        "sri_environment": "testing",
        "certificate_secret_arn": "arn:aws:secretsmanager:us-east-1:1234:secret:cert",
        "monthly_limit": -1,
        "doc_type": "01",
        "serie": "001001",
        "issued_at": _TODAY,
        "client_id": None,
        "buyer_id_type": "07",
        "buyer_id": "9999999999999",
        "buyer_name": "Consumidor Final",
        "buyer_email": None,
        "payment_method": "01",
        "lines": [
            LineData(
                code="001",
                description="Producto A",
                quantity=Decimal("2"),
                unit_price=Decimal("10.00"),
                discount=Decimal("0.00"),
                iva_rate="15",
            )
        ],
        "created_by": "user-1",
    }
    defaults.update(overrides)
    return EmitDocumentCommand(**defaults)


def _make_document(**overrides: Any) -> Document:
    defaults: dict[str, Any] = {
        "document_id": "doc-1",
        "tenant_id": "t-1",
        "doc_type": "01",
        "status": DocumentStatus.AUTHORIZED,
        "serie": "001001",
        "sequential": 1,
        "access_key": "1" * 49,
        "client_id": None,
        "buyer_id_type": "07",
        "buyer_id": "9999999999999",
        "buyer_name": "Consumidor Final",
        "buyer_email": None,
        "issued_at": _TODAY,
        "sri_environment": "testing",
        "subtotal": Decimal("20.00"),
        "total_discount": Decimal("0.00"),
        "iva_15": Decimal("3.00"),
        "iva_5": Decimal("0.00"),
        "iva_0": Decimal("0.00"),
        "total": Decimal("23.00"),
        "payment_method": "01",
        "lines": [],
    }
    defaults.update(overrides)
    return Document(**defaults)


# ── EmitDocumentUseCase ───────────────────────────────────────────────────────


class EmitDocumentUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = FakeDocumentsRepository()
        self.seq = FakeSequencesPort(next_value=5)

    def _run(self, **overrides: Any) -> Document:
        with patch("lambdas.documents.use_cases.emit_document.today_ecuador", return_value=_TODAY):
            return EmitDocumentUseCase(self.repo, self.seq).execute(_make_emit_cmd(**overrides))

    def _run_with_catalog(self, **overrides: Any) -> Document:
        with patch("lambdas.documents.use_cases.emit_document.today_ecuador", return_value=_TODAY):
            return EmitDocumentUseCase(self.repo, self.seq, FakeProductCatalog()).execute(
                _make_emit_cmd(**overrides)
            )

    def _run_with(self, *, catalog=None, campaign=None, **overrides: Any) -> Document:
        with patch("lambdas.documents.use_cases.emit_document.today_ecuador", return_value=_TODAY):
            return EmitDocumentUseCase(self.repo, self.seq, catalog, campaign).execute(
                _make_emit_cmd(**overrides)
            )

    def test_returns_pending_document(self) -> None:
        doc = self._run()
        self.assertEqual(doc.status, DocumentStatus.PENDING)
        self.assertEqual(doc.tenant_id, "t-1")
        self.assertEqual(doc.serie, "001001")
        self.assertEqual(doc.sequential, 5)
        self.assertEqual(len(doc.access_key), 49)
        self.assertEqual(self.repo.save_calls, [])

    def test_computes_totals_correctly(self) -> None:
        # 2 units × 10.00 - 0 discount = 20.00 subtotal; IVA 15% = 3.00; total = 23.00
        doc = self._run()
        self.assertEqual(doc.subtotal, Decimal("20.00"))
        self.assertEqual(doc.iva_15, Decimal("3.00"))
        self.assertEqual(doc.total, Decimal("23.00"))

    def test_raises_without_certificate(self) -> None:
        with self.assertRaises(CertificateNotUploadedError):
            self._run(certificate_secret_arn=None)

    def test_raises_for_future_issued_at(self) -> None:
        with self.assertRaises(InvalidIssuedDateError):
            self._run(issued_at=date(2027, 1, 1))

    def test_raises_when_limit_reached(self) -> None:
        self.repo.set_month_count(10)
        with self.assertRaises(DocumentLimitReachedError):
            self._run(monthly_limit=10)

    def test_unlimited_plan_skips_limit_check(self) -> None:
        self.repo.set_month_count(9999)
        doc = self._run(monthly_limit=-1)
        self.assertEqual(doc.status, DocumentStatus.PENDING)

    def test_consumidor_final_fields(self) -> None:
        doc = self._run(
            buyer_id_type="07",
            buyer_id="9999999999999",
            buyer_name="Consumidor Final",
            client_id=None,
        )
        self.assertIsNone(doc.client_id)
        self.assertEqual(doc.buyer_id, "9999999999999")

    def test_exento_line_no_iva(self) -> None:
        lines = [
            LineData(
                code="EX-01",
                description="Producto Exento",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
                discount=Decimal("0.00"),
                iva_rate="EXENTO",
            )
        ]
        doc = self._run(lines=lines)
        self.assertEqual(doc.iva_15, Decimal("0.00"))
        self.assertEqual(doc.total, Decimal("100.00"))

    def test_iva_5_line(self) -> None:
        lines = [
            LineData(
                code="R-01",
                description="Producto 5%",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
                discount=Decimal("0.00"),
                iva_rate="5",
            )
        ]
        doc = self._run(lines=lines)
        self.assertEqual(doc.iva_5, Decimal("5.00"))
        self.assertEqual(doc.total, Decimal("105.00"))

    def test_product_line_uses_catalog_snapshot(self) -> None:
        lines = [
            LineData(
                product_id="prod-1",
                code="MANUAL",
                description="Manual",
                quantity=Decimal("2"),
                unit_price=Decimal("1.00"),
                discount=Decimal("0.00"),
                iva_rate="15",
            )
        ]

        doc = self._run_with_catalog(lines=lines)

        self.assertEqual(doc.lines[0].product_id, "prod-1")
        self.assertEqual(doc.lines[0].code, "SKU-001")
        self.assertEqual(doc.lines[0].description, "Servicio desde catálogo")
        self.assertEqual(doc.lines[0].unit_price, Decimal("30.00"))
        self.assertEqual(doc.iva_5, Decimal("3.00"))
        self.assertEqual(doc.total, Decimal("63.00"))

    def test_rejects_line_with_zero_unit_price(self) -> None:
        lines = [
            LineData(
                code="P-0",
                description="Producto sin precio",
                quantity=Decimal("1"),
                unit_price=Decimal("0.00"),
                discount=Decimal("0.00"),
                iva_rate="15",
            )
        ]

        with self.assertRaises(ValidationError):
            self._run(lines=lines)

    def test_rejects_discount_above_line_gross(self) -> None:
        lines = [
            LineData(
                code="P-1",
                description="Producto con descuento inválido",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                discount=Decimal("10.01"),
                iva_rate="15",
            )
        ]

        with self.assertRaises(ValidationError):
            self._run(lines=lines)

    # ── Discount ceiling (catalog % + campaign %, "el mayor gana") ───────────

    def test_rejects_manual_line_discount_with_no_campaign_or_product_discount(self) -> None:
        lines = [
            LineData(
                code="P-1",
                description="Línea manual",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                discount=Decimal("1.00"),
                iva_rate="15",
            )
        ]

        with self.assertRaises(ValidationError):
            self._run_with(lines=lines)

    def test_allows_discount_up_to_product_discount_percentage(self) -> None:
        lines = [
            LineData(
                product_id="prod-2",
                code="MANUAL",
                description="Manual",
                quantity=Decimal("1"),
                unit_price=Decimal("1.00"),
                discount=Decimal("18.00"),  # 60% of the 30.00 catalog price
                iva_rate="15",
            )
        ]

        doc = self._run_with(catalog=FakeProductCatalog(), lines=lines)

        self.assertEqual(doc.lines[0].discount, Decimal("18.00"))

    def test_rejects_discount_above_product_discount_percentage(self) -> None:
        lines = [
            LineData(
                product_id="prod-2",
                code="MANUAL",
                description="Manual",
                quantity=Decimal("1"),
                unit_price=Decimal("1.00"),
                discount=Decimal("18.01"),  # just above 60% of 30.00
                iva_rate="15",
            )
        ]

        with self.assertRaises(ValidationError):
            self._run_with(catalog=FakeProductCatalog(), lines=lines)

    def test_allows_discount_up_to_active_campaign_percentage_on_manual_line(self) -> None:
        lines = [
            LineData(
                code="P-1",
                description="Línea manual",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
                discount=Decimal("50.00"),
                iva_rate="15",
            )
        ]

        doc = self._run_with(
            campaign=FakeDiscountCampaignPort(active=True, percentage=Decimal("50")),
            lines=lines,
        )

        self.assertEqual(doc.lines[0].discount, Decimal("50.00"))

    def test_ceiling_uses_max_of_product_and_campaign_not_their_sum(self) -> None:
        lines = [
            LineData(
                product_id="prod-2",  # 60% product discount
                code="MANUAL",
                description="Manual",
                quantity=Decimal("1"),
                unit_price=Decimal("1.00"),
                discount=Decimal("20.00"),  # above 60% (18.00), would fit if summed with 30%
                iva_rate="15",
            )
        ]

        with self.assertRaises(ValidationError):
            self._run_with(
                catalog=FakeProductCatalog(),
                campaign=FakeDiscountCampaignPort(active=True, percentage=Decimal("30")),
                lines=lines,
            )

    def test_inactive_campaign_does_not_raise_ceiling(self) -> None:
        lines = [
            LineData(
                code="P-1",
                description="Línea manual",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
                discount=Decimal("0.00"),
                iva_rate="15",
            )
        ]

        doc = self._run_with(
            campaign=FakeDiscountCampaignPort(active=False, percentage=Decimal("50")),
            lines=lines,
        )

        self.assertEqual(doc.lines[0].discount, Decimal("0.00"))

    def test_override_bypasses_discount_ceiling(self) -> None:
        lines = [
            LineData(
                code="P-1",
                description="Descuento comercial puntual",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                discount=Decimal("5.00"),
                iva_rate="15",
            )
        ]

        doc = self._run_with(
            lines=lines,
            override_discount_ceiling=True,
            override_reason="Gesto comercial autorizado por el gerente",
        )

        self.assertEqual(doc.lines[0].discount, Decimal("5.00"))

    def test_override_without_reason_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self._run_with(override_discount_ceiling=True, override_reason="")

    def test_override_without_reason_at_all_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self._run_with(override_discount_ceiling=True, override_reason=None)


# ── GetDocumentUseCase ────────────────────────────────────────────────────────


class GetDocumentUseCaseTests(unittest.TestCase):
    def test_returns_document(self) -> None:
        repo = FakeDocumentsRepository()
        doc = _make_document()
        repo.seed(doc)

        result = GetDocumentUseCase(repo).execute(GetDocumentCommand("t-1", "doc-1"))
        self.assertEqual(result.document_id, "doc-1")

    def test_raises_if_not_found(self) -> None:
        repo = FakeDocumentsRepository()
        with self.assertRaises(DocumentNotFoundError):
            GetDocumentUseCase(repo).execute(GetDocumentCommand("t-1", "missing"))


# ── ListDocumentsUseCase ──────────────────────────────────────────────────────


class ListDocumentsUseCaseTests(unittest.TestCase):
    def test_returns_empty_list(self) -> None:
        repo = FakeDocumentsRepository()
        docs, cursor = ListDocumentsUseCase(repo).execute(ListDocumentsCommand(tenant_id="t-1"))
        self.assertEqual(docs, [])
        self.assertIsNone(cursor)

    def test_filters_by_tenant(self) -> None:
        repo = FakeDocumentsRepository()
        repo.seed(_make_document(tenant_id="t-1", document_id="d1"))
        repo.seed(_make_document(tenant_id="t-2", document_id="d2"))

        docs, _ = ListDocumentsUseCase(repo).execute(ListDocumentsCommand(tenant_id="t-1"))
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].document_id, "d1")

    def test_count_delegates_to_repository(self) -> None:
        repo = FakeDocumentsRepository()
        repo.count_result = 12

        total = ListDocumentsUseCase(repo).count(
            ListDocumentsCommand(tenant_id="t-1", status="AUTHORIZED")
        )

        self.assertEqual(total, 12)
        self.assertEqual(repo.count_calls[0]["tenant_id"], "t-1")
        self.assertEqual(repo.count_calls[0]["status"], "AUTHORIZED")


# ── GetRideUrlUseCase ─────────────────────────────────────────────────────────


class GetRideUrlUseCaseTests(unittest.TestCase):
    def test_returns_presigned_url(self) -> None:
        repo = FakeDocumentsRepository()
        doc = _make_document(
            status=DocumentStatus.AUTHORIZED,
            ride_s3_key="tenants/t-1/docs/2026/doc-1.pdf",
        )
        repo.seed(doc)

        from lambdas.documents.domain.commands import GetRideUrlCommand

        with patch("lambdas.documents.use_cases.get_ride_url.boto3") as mock_boto3:
            mock_boto3.client.return_value.generate_presigned_url.return_value = (
                "https://s3.example.com/signed"
            )
            url = GetRideUrlUseCase(repo).execute(GetRideUrlCommand("t-1", "doc-1", "my-bucket"))

        self.assertEqual(url, "https://s3.example.com/signed")

    def test_raises_if_ride_not_available(self) -> None:
        repo = FakeDocumentsRepository()
        doc = _make_document(status=DocumentStatus.PENDING, ride_s3_key=None)
        repo.seed(doc)

        from lambdas.documents.domain.commands import GetRideUrlCommand

        with self.assertRaises(RideNotAvailableError):
            GetRideUrlUseCase(repo).execute(GetRideUrlCommand("t-1", "doc-1", "my-bucket"))
