from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class LineData:
    code: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    iva_rate: str  # "15" | "5" | "0" | "EXENTO"
    product_id: str | None = None


@dataclass
class EmitDocumentCommand:
    tenant_id: str
    ruc: str
    sri_environment: str  # "testing" | "production"
    certificate_secret_arn: str | None
    monthly_limit: int  # -1 = unlimited; from plan, adjusted for environment
    doc_type: str
    serie: str  # e.g. "001001"
    issued_at: date
    client_id: str | None
    buyer_id_type: str
    buyer_id: str
    buyer_name: str
    buyer_email: str | None
    payment_method: str
    lines: list[LineData]
    created_by: str
    override_discount_ceiling: bool = False
    override_reason: str | None = None


@dataclass
class CreditNoteLineData:
    parent_line_index: int
    quantity: Decimal


@dataclass
class EmitCreditNoteCommand:
    tenant_id: str
    ruc: str
    sri_environment: str  # "testing" | "production"
    certificate_secret_arn: str | None
    monthly_limit: int
    serie: str  # e.g. "001001" — punto de emision de la nota de credito
    issued_at: date
    related_document_id: str
    credit_note_reason: str
    lines: list[CreditNoteLineData]
    created_by: str


@dataclass
class GetDocumentCommand:
    tenant_id: str
    document_id: str


@dataclass
class ListDocumentsCommand:
    tenant_id: str
    status: str | None = None
    doc_type: str | None = None
    serie: str | None = None
    q: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    limit: int = 20
    cursor: str | None = None


@dataclass
class GetRideUrlCommand:
    tenant_id: str
    document_id: str
    documents_bucket: str


@dataclass
class GetXmlUrlCommand:
    tenant_id: str
    document_id: str
    documents_bucket: str


@dataclass
class AnnulDocumentCommand:
    tenant_id: str
    document_id: str
    reason: str
    user_id: str


@dataclass
class RetryDocumentCommand:
    tenant_id: str
    document_id: str
    user_id: str
