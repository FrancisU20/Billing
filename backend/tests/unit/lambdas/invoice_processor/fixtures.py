from __future__ import annotations

from datetime import date
from decimal import Decimal

from lambdas.documents.domain.entities import Document, DocumentStatus, InvoiceLine
from tests.unit.support import make_tenant

ACCESS_KEY = "1" * 49


def make_line(**overrides) -> InvoiceLine:
    defaults = dict(
        code="P1",
        description="Producto 1",
        quantity=Decimal("2"),
        unit_price=Decimal("10.00"),
        discount=Decimal("0.00"),
        subtotal=Decimal("20.00"),
        iva_rate="15",
        iva_amount=Decimal("3.00"),
        total=Decimal("23.00"),
    )
    defaults.update(overrides)
    return InvoiceLine(**defaults)


def make_document(**overrides) -> Document:
    defaults = dict(
        document_id="doc-1",
        tenant_id="tenant-1",
        doc_type="01",
        status=DocumentStatus.PENDING,
        serie="001001",
        sequential=1,
        access_key=ACCESS_KEY,
        client_id=None,
        buyer_id_type="07",
        buyer_id="9999999999999",
        buyer_name="CONSUMIDOR FINAL",
        buyer_email=None,
        issued_at=date(2026, 6, 17),
        sri_environment="testing",
        subtotal=Decimal("20.00"),
        total_discount=Decimal("0.00"),
        iva_15=Decimal("3.00"),
        iva_5=Decimal("0.00"),
        iva_0=Decimal("0.00"),
        total=Decimal("23.00"),
        payment_method="01",
        lines=[make_line()],
    )
    defaults.update(overrides)
    return Document(**defaults)


def make_invoice_tenant(**overrides):
    defaults = dict(
        address="Av Siempre Viva 123",
        certificate_secret_arn="arn:aws:secretsmanager:sa-east-1:123:secret:tenant-1/certificate",
    )
    defaults.update(overrides)
    return make_tenant(**defaults)
