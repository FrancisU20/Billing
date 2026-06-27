from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from lambdas.documents.domain.commands import (
    AnnulDocumentCommand,
    CreditNoteLineData,
    EmitCreditNoteCommand,
    EmitDocumentCommand,
    GetDocumentCommand,
    GetXmlUrlCommand,
    LineData,
    ListDocumentsCommand,
    RetryDocumentCommand,
)
from lambdas.documents.domain.entities import (
    Document,
    DocumentStatus,
    DocumentSummary,
    InvoiceLine,
)
from lambdas.documents.domain.errors import (
    AnnulmentWindowExpiredError,
    CertificateNotUploadedError,
    ConsumerFinalCannotBeAnnulledError,
    CreditedQuantityExceedsOriginalError,
    DocumentLimitReachedError,
    DocumentNotAuthorizedError,
    DocumentNotFoundError,
    DocumentRetryNotEligibleError,
    InvalidIssuedDateError,
    ParentAlreadyAnnulledError,
    ParentDocumentNotAuthorizedError,
    RideNotAvailableError,
    XmlNotAvailableError,
)
from lambdas.documents.domain.repositories.i_discount_campaign_port import (
    DiscountCampaignSnapshot,
)
from lambdas.documents.domain.repositories.i_product_catalog import InvoiceProductSnapshot
from lambdas.documents.use_cases.annul_document import AnnulDocumentUseCase
from lambdas.documents.use_cases.emit_credit_note import EmitCreditNoteUseCase
from lambdas.documents.use_cases.emit_document import EmitDocumentUseCase
from lambdas.documents.use_cases.get_document import GetDocumentUseCase
from lambdas.documents.use_cases.get_documents_summary import GetDocumentsSummaryUseCase
from lambdas.documents.use_cases.get_ride_url import GetRideUrlUseCase
from lambdas.documents.use_cases.get_xml_url import GetXmlUrlUseCase
from lambdas.documents.use_cases.list_documents import ListDocumentsUseCase
from lambdas.documents.use_cases.retry_document import RetryDocumentUseCase
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
        self.summary_result = DocumentSummary(
            period_start="2026-06-01",
            period_end="2026-06-17",
            issued_count=0,
            authorized_count=0,
            rejected_count=0,
            failed_count=0,
            pending_count=0,
            processing_count=0,
            authorized_total=Decimal("0.00"),
        )
        self.list_calls: list[dict[str, Any]] = []
        self.count_calls: list[dict[str, Any]] = []
        self.mark_annulled_calls: list[tuple[str, str, str]] = []

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
        self.list_calls.append({"tenant_id": tenant_id, **kwargs})
        docs = [d for d in self.documents.values() if d.tenant_id == tenant_id]
        return docs, None

    def count_this_month(self, tenant_id: str, sri_environment: str) -> int:
        return self._month_count

    def count(self, tenant_id: str, **kwargs: Any) -> int:
        self.count_calls.append({"tenant_id": tenant_id, **kwargs})
        return self.count_result

    def summary_this_month(self, tenant_id: str) -> DocumentSummary:
        return self.summary_result

    def save(self, document: Document, **kwargs: Any) -> None:
        self.save_calls.append(document)
        self.documents[f"{document.tenant_id}#{document.document_id}"] = document

    def retry(self, tenant_id: str, document_id: str, **kwargs: Any) -> None:
        key = f"{tenant_id}#{document_id}"
        doc = self.documents.get(key)
        if doc is None or doc.status != DocumentStatus.REJECTED:
            raise DocumentRetryNotEligibleError()
        self.documents[key] = replace(
            doc, status=DocumentStatus.PENDING, manual_retry_count=doc.manual_retry_count + 1
        )

    def mark_annulled_by_credit_note(
        self, tenant_id: str, document_id: str, *, credit_note_id: str
    ) -> None:
        self.mark_annulled_calls.append((tenant_id, document_id, credit_note_id))
        key = f"{tenant_id}#{document_id}"
        doc = self.documents.get(key)
        if doc is not None:
            self.documents[key] = replace(doc, annulled_by_credit_note_id=credit_note_id)

    def seed(self, document: Document) -> None:
        self.documents[f"{document.tenant_id}#{document.document_id}"] = document

    def set_month_count(self, count: int) -> None:
        self._month_count = count


class FakeSequencesPort:
    def __init__(self, next_value: int = 1) -> None:
        self._next = next_value
        self.reserve_calls: list[tuple[str, str, str]] = []

    def reserve_next(self, tenant_id: str, serie: str, doc_type: str = "01") -> int:
        self.reserve_calls.append((tenant_id, serie, doc_type))
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
        self.assertEqual(doc.buyer_name, "CONSUMIDOR FINAL")

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


# ── EmitCreditNoteUseCase ─────────────────────────────────────────────────────


def _make_credit_note_cmd(**overrides: Any) -> EmitCreditNoteCommand:
    defaults: dict[str, Any] = {
        "tenant_id": "t-1",
        "ruc": "1790000000001",
        "sri_environment": "testing",
        "certificate_secret_arn": "arn:aws:secretsmanager:us-east-1:1234:secret:cert",
        "monthly_limit": -1,
        "serie": "001001",
        "issued_at": _TODAY,
        "related_document_id": "doc-1",
        "credit_note_reason": "Devolución de mercadería",
        "lines": [CreditNoteLineData(parent_line_index=0, quantity=Decimal("2"))],
        "created_by": "user-1",
    }
    defaults.update(overrides)
    return EmitCreditNoteCommand(**defaults)


def _make_parent_invoice(**overrides: Any) -> Document:
    defaults: dict[str, Any] = {
        "status": DocumentStatus.AUTHORIZED,
        "lines": [
            InvoiceLine(
                code="001",
                description="Producto A",
                quantity=Decimal("2"),
                unit_price=Decimal("10.00"),
                discount=Decimal("0.00"),
                subtotal=Decimal("20.00"),
                iva_rate="15",
                iva_amount=Decimal("3.00"),
                total=Decimal("23.00"),
            )
        ],
    }
    defaults.update(overrides)
    return _make_document(**defaults)


class EmitCreditNoteUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = FakeDocumentsRepository()
        self.seq = FakeSequencesPort(next_value=1)
        self.repo.seed(_make_parent_invoice())

    def _run(self, **overrides: Any) -> tuple[Document, bool]:
        with patch(
            "lambdas.documents.use_cases.emit_credit_note.today_ecuador", return_value=_TODAY
        ):
            return EmitCreditNoteUseCase(self.repo, self.seq).execute(
                _make_credit_note_cmd(**overrides)
            )

    def test_full_credit_copies_parent_buyer_and_lines(self) -> None:
        doc, is_full_annulment = self._run()
        self.assertEqual(doc.doc_type, "04")
        self.assertEqual(doc.status, DocumentStatus.PENDING)
        self.assertEqual(doc.related_document_id, "doc-1")
        self.assertEqual(doc.credit_note_reason, "Devolución de mercadería")
        self.assertEqual(doc.buyer_id, "9999999999999")
        self.assertEqual(doc.buyer_name, "Consumidor Final")
        self.assertEqual(doc.subtotal, Decimal("20.00"))
        self.assertEqual(doc.iva_15, Decimal("3.00"))
        self.assertEqual(doc.total, Decimal("23.00"))
        self.assertEqual(len(doc.lines), 1)
        self.assertEqual(doc.lines[0].quantity, Decimal("2"))
        # Acredita el 100% de la unica linea de la factura -> es anulacion completa.
        self.assertTrue(is_full_annulment)

    def test_partial_credit_scales_amounts_proportionally(self) -> None:
        doc, is_full_annulment = self._run(
            lines=[CreditNoteLineData(parent_line_index=0, quantity=Decimal("1"))]
        )
        # Mitad de la cantidad original (1 de 2) -> mitad de subtotal/iva/total.
        self.assertEqual(doc.subtotal, Decimal("10.00"))
        self.assertEqual(doc.iva_15, Decimal("1.50"))
        self.assertEqual(doc.total, Decimal("11.50"))
        self.assertEqual(doc.lines[0].quantity, Decimal("1"))
        self.assertFalse(is_full_annulment)

    def test_reserves_sequential_with_doc_type_04(self) -> None:
        self._run()
        self.assertEqual(self.seq.reserve_calls, [("t-1", "001001", "04")])

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

    def test_raises_empty_reason(self) -> None:
        with self.assertRaises(ValidationError):
            self._run(credit_note_reason="   ")

    def test_raises_if_parent_not_found(self) -> None:
        with self.assertRaises(DocumentNotFoundError):
            self._run(related_document_id="does-not-exist")

    def test_raises_if_parent_not_authorized(self) -> None:
        self.repo.seed(_make_parent_invoice(document_id="doc-2", status=DocumentStatus.PENDING))
        with self.assertRaises(ParentDocumentNotAuthorizedError):
            self._run(related_document_id="doc-2")

    def test_raises_if_parent_is_a_credit_note(self) -> None:
        self.repo.seed(_make_parent_invoice(document_id="doc-2", doc_type="04"))
        with self.assertRaises(ValidationError):
            self._run(related_document_id="doc-2")

    def test_raises_if_credited_quantity_exceeds_original(self) -> None:
        with self.assertRaises(CreditedQuantityExceedsOriginalError):
            self._run(lines=[CreditNoteLineData(parent_line_index=0, quantity=Decimal("3"))])

    def test_raises_if_line_index_out_of_range(self) -> None:
        with self.assertRaises(ValidationError):
            self._run(lines=[CreditNoteLineData(parent_line_index=5, quantity=Decimal("1"))])

    def test_raises_if_parent_already_annulled(self) -> None:
        self.repo.seed(_make_parent_invoice(annulled_by_credit_note_id="existing-cn-1"))
        with self.assertRaises(ParentAlreadyAnnulledError):
            self._run()

    def test_full_annulment_with_lines_out_of_order(self) -> None:
        # Factura con 2 lineas; la NC las acredita en orden inverso (indice 1 antes que
        # el 0) — el calculo de is_full_annulment usa parent_line_index explicito, no la
        # posicion en la lista resultante, asi que esto SI debe contar como 100%.
        self.repo.seed(
            _make_parent_invoice(
                document_id="doc-2",
                lines=[
                    InvoiceLine(
                        code="001",
                        description="Producto A",
                        quantity=Decimal("2"),
                        unit_price=Decimal("10.00"),
                        discount=Decimal("0.00"),
                        subtotal=Decimal("20.00"),
                        iva_rate="15",
                        iva_amount=Decimal("3.00"),
                        total=Decimal("23.00"),
                    ),
                    InvoiceLine(
                        code="002",
                        description="Producto B",
                        quantity=Decimal("1"),
                        unit_price=Decimal("5.00"),
                        discount=Decimal("0.00"),
                        subtotal=Decimal("5.00"),
                        iva_rate="15",
                        iva_amount=Decimal("0.75"),
                        total=Decimal("5.75"),
                    ),
                ],
            )
        )
        _, is_full_annulment = self._run(
            related_document_id="doc-2",
            lines=[
                CreditNoteLineData(parent_line_index=1, quantity=Decimal("1")),
                CreditNoteLineData(parent_line_index=0, quantity=Decimal("2")),
            ],
        )
        self.assertTrue(is_full_annulment)

    def test_not_full_annulment_when_a_line_is_missing(self) -> None:
        # Misma factura de 2 lineas, pero la NC solo acredita la linea 0 al 100% —
        # la linea 1 queda sin acreditar, no es anulacion completa de la factura.
        self.repo.seed(
            _make_parent_invoice(
                document_id="doc-2",
                lines=[
                    InvoiceLine(
                        code="001",
                        description="Producto A",
                        quantity=Decimal("2"),
                        unit_price=Decimal("10.00"),
                        discount=Decimal("0.00"),
                        subtotal=Decimal("20.00"),
                        iva_rate="15",
                        iva_amount=Decimal("3.00"),
                        total=Decimal("23.00"),
                    ),
                    InvoiceLine(
                        code="002",
                        description="Producto B",
                        quantity=Decimal("1"),
                        unit_price=Decimal("5.00"),
                        discount=Decimal("0.00"),
                        subtotal=Decimal("5.00"),
                        iva_rate="15",
                        iva_amount=Decimal("0.75"),
                        total=Decimal("5.75"),
                    ),
                ],
            )
        )
        _, is_full_annulment = self._run(
            related_document_id="doc-2",
            lines=[CreditNoteLineData(parent_line_index=0, quantity=Decimal("2"))],
        )
        self.assertFalse(is_full_annulment)


# ── GetDocumentUseCase ────────────────────────────────────────────────────────


class GetDocumentsSummaryUseCaseTests(unittest.TestCase):
    def test_returns_repository_month_summary(self) -> None:
        repo = FakeDocumentsRepository()
        repo.summary_result = DocumentSummary(
            period_start="2026-06-01",
            period_end="2026-06-17",
            issued_count=7,
            authorized_count=5,
            rejected_count=1,
            failed_count=1,
            pending_count=0,
            processing_count=0,
            authorized_total=Decimal("123.45"),
        )

        summary = GetDocumentsSummaryUseCase(repo).execute("t-1")

        self.assertEqual(summary.issued_count, 7)
        self.assertEqual(summary.authorized_total, Decimal("123.45"))
        self.assertIsNone(summary.document_limit)
        self.assertFalse(summary.is_unlimited)

    def test_attaches_monthly_limit_when_provided(self) -> None:
        repo = FakeDocumentsRepository()
        repo.summary_result = DocumentSummary(
            period_start="2026-06-01",
            period_end="2026-06-17",
            issued_count=7,
            authorized_count=5,
            rejected_count=1,
            failed_count=1,
            pending_count=0,
            processing_count=0,
            authorized_total=Decimal("123.45"),
        )

        summary = GetDocumentsSummaryUseCase(repo).execute("t-1", monthly_limit=500)

        self.assertEqual(summary.document_limit, 500)
        self.assertFalse(summary.is_unlimited)

    def test_marks_free_plan_when_provided(self) -> None:
        repo = FakeDocumentsRepository()
        repo.summary_result = DocumentSummary(
            period_start="2026-06-01",
            period_end="2026-06-17",
            issued_count=7,
            authorized_count=5,
            rejected_count=1,
            failed_count=1,
            pending_count=0,
            processing_count=0,
            authorized_total=Decimal("123.45"),
        )

        summary = GetDocumentsSummaryUseCase(repo).execute(
            "t-1",
            monthly_limit=20,
            is_free_plan=True,
        )

        self.assertEqual(summary.document_limit, 20)
        self.assertTrue(summary.is_free_plan)

    def test_marks_unlimited_for_sentinel_value(self) -> None:
        repo = FakeDocumentsRepository()
        repo.summary_result = DocumentSummary(
            period_start="2026-06-01",
            period_end="2026-06-17",
            issued_count=7,
            authorized_count=5,
            rejected_count=1,
            failed_count=1,
            pending_count=0,
            processing_count=0,
            authorized_total=Decimal("123.45"),
        )

        summary = GetDocumentsSummaryUseCase(repo).execute("t-1", monthly_limit=-1)

        self.assertEqual(summary.document_limit, -1)
        self.assertTrue(summary.is_unlimited)


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

    def test_execute_delegates_search_query_to_repository(self) -> None:
        repo = FakeDocumentsRepository()

        ListDocumentsUseCase(repo).execute(ListDocumentsCommand(tenant_id="t-1", q="Ulloa"))

        self.assertEqual(repo.list_calls[0]["tenant_id"], "t-1")
        self.assertEqual(repo.list_calls[0]["q"], "Ulloa")


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


# ── GetXmlUrlUseCase ──────────────────────────────────────────────────────────


class GetXmlUrlUseCaseTests(unittest.TestCase):
    def test_returns_presigned_url(self) -> None:
        repo = FakeDocumentsRepository()
        doc = _make_document(
            status=DocumentStatus.AUTHORIZED,
            xml_s3_key="tenants/t-1/docs/2026/doc-1.xml",
        )
        repo.seed(doc)

        with patch("lambdas.documents.use_cases.get_xml_url.boto3") as mock_boto3:
            mock_boto3.client.return_value.generate_presigned_url.return_value = (
                "https://s3.example.com/signed-xml"
            )
            url = GetXmlUrlUseCase(repo).execute(GetXmlUrlCommand("t-1", "doc-1", "my-bucket"))

        self.assertEqual(url, "https://s3.example.com/signed-xml")

    def test_raises_if_xml_not_available(self) -> None:
        repo = FakeDocumentsRepository()
        doc = _make_document(status=DocumentStatus.PENDING, xml_s3_key=None)
        repo.seed(doc)

        with self.assertRaises(XmlNotAvailableError):
            GetXmlUrlUseCase(repo).execute(GetXmlUrlCommand("t-1", "doc-1", "my-bucket"))


# ── AnnulDocumentUseCase ──────────────────────────────────────────────────────


class AnnulDocumentUseCaseTests(unittest.TestCase):
    def _run(self, **overrides: Any) -> Document:
        repo = FakeDocumentsRepository()
        defaults: dict[str, Any] = {
            "status": DocumentStatus.AUTHORIZED,
            "buyer_id_type": "05",
            "issued_at": _TODAY,
        }
        doc = _make_document(**{**defaults, **overrides})
        repo.seed(doc)
        with patch("lambdas.documents.use_cases.annul_document.today_ecuador", return_value=_TODAY):
            return AnnulDocumentUseCase(repo).execute(
                AnnulDocumentCommand(
                    tenant_id="t-1",
                    document_id="doc-1",
                    reason="Error en el monto facturado",
                    user_id="user-1",
                )
            )

    def test_annuls_authorized_document_within_window(self) -> None:
        result = self._run()

        self.assertEqual(result.status, DocumentStatus.ANNULLED)
        self.assertEqual(result.annulled_by, "user-1")
        self.assertEqual(result.annulment_reason, "Error en el monto facturado")
        self.assertIsNotNone(result.annulled_at)

    def test_raises_if_not_authorized(self) -> None:
        with self.assertRaises(DocumentNotAuthorizedError):
            self._run(status=DocumentStatus.PENDING)

    def test_raises_for_consumidor_final(self) -> None:
        with self.assertRaises(ConsumerFinalCannotBeAnnulledError):
            self._run(buyer_id_type="07")

    def test_raises_if_window_expired(self) -> None:
        with self.assertRaises(AnnulmentWindowExpiredError):
            self._run(issued_at=date(2026, 1, 1))


class RetryDocumentUseCaseTests(unittest.TestCase):
    def _run(self, **overrides: Any) -> Document:
        repo = FakeDocumentsRepository()
        defaults: dict[str, Any] = {
            "status": DocumentStatus.REJECTED,
            "manual_retry_count": 0,
        }
        doc = _make_document(**{**defaults, **overrides})
        repo.seed(doc)
        return RetryDocumentUseCase(repo).execute(
            RetryDocumentCommand(tenant_id="t-1", document_id="doc-1", user_id="user-1")
        )

    def test_retries_rejected_document_back_to_pending(self) -> None:
        result = self._run()

        self.assertEqual(result.status, DocumentStatus.PENDING)
        self.assertEqual(result.manual_retry_count, 1)
        self.assertIsNotNone(result.retried_at)
        # Misma clave de acceso/secuencial — el reintento NUNCA genera numeros nuevos.
        self.assertEqual(result.access_key, "1" * 49)
        self.assertEqual(result.sequential, 1)

    def test_increments_manual_retry_count_on_each_retry(self) -> None:
        result = self._run(manual_retry_count=2)

        self.assertEqual(result.manual_retry_count, 3)

    def test_raises_if_not_rejected(self) -> None:
        with self.assertRaises(DocumentRetryNotEligibleError):
            self._run(status=DocumentStatus.AUTHORIZED)

    def test_raises_if_pending(self) -> None:
        with self.assertRaises(DocumentRetryNotEligibleError):
            self._run(status=DocumentStatus.PENDING)

    def test_raises_if_failed_permanent(self) -> None:
        # Deliberado: FAILED_PERMANENT necesita re-poll, no re-sign — fuera de alcance.
        with self.assertRaises(DocumentRetryNotEligibleError):
            self._run(status=DocumentStatus.FAILED_PERMANENT)
