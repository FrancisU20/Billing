from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from shared.dates import isoformat_ecuador, now_utc


def _now() -> datetime:
    return now_utc()


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    AUTHORIZED = "AUTHORIZED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    FAILED_PERMANENT = "FAILED_PERMANENT"
    ANNULLED = "ANNULLED"


class BuyerNotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    SKIPPED_NO_EMAIL = "SKIPPED_NO_EMAIL"
    FAILED = "FAILED"


@dataclass(frozen=True)
class DailyIssuedCount:
    date: str
    count: int

    def to_dict(self) -> dict:
        return {"date": self.date, "count": self.count}


@dataclass(frozen=True)
class TopClientTotal:
    client_id: str
    name: str
    total: Decimal

    def to_dict(self) -> dict:
        return {"client_id": self.client_id, "name": self.name, "total": str(self.total)}


@dataclass(frozen=True)
class DocumentSummary:
    period_start: str
    period_end: str
    issued_count: int
    authorized_count: int
    rejected_count: int
    failed_count: int
    pending_count: int
    processing_count: int
    authorized_total: Decimal
    document_limit: int | None = None
    is_unlimited: bool = False
    is_free_plan: bool = False
    daily_issued: list[DailyIssuedCount] = field(default_factory=list)
    top_clients: list[TopClientTotal] = field(default_factory=list)
    # Notas de credito (doc_type="04") restan de authorized_total (ingreso neto) en vez
    # de sumarse como factura — estos dos campos exponen ese monto por separado para
    # transparencia en el dashboard, sin que el tenant tenga que inferirlo.
    credit_notes_count: int = 0
    credit_notes_total: Decimal = Decimal("0.00")

    def to_dict(self) -> dict:
        return {
            "period_start": self.period_start,
            "period_end": self.period_end,
            "issued_count": self.issued_count,
            "authorized_count": self.authorized_count,
            "rejected_count": self.rejected_count,
            "failed_count": self.failed_count,
            "pending_count": self.pending_count,
            "processing_count": self.processing_count,
            "authorized_total": str(self.authorized_total),
            "credit_notes_count": self.credit_notes_count,
            "credit_notes_total": str(self.credit_notes_total),
            "document_limit": self.document_limit,
            "is_unlimited": self.is_unlimited,
            "is_free_plan": self.is_free_plan,
            "daily_issued": [d.to_dict() for d in self.daily_issued],
            "top_clients": [c.to_dict() for c in self.top_clients],
        }


@dataclass
class InvoiceLine:
    code: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    subtotal: Decimal
    iva_rate: str  # "15" | "5" | "0" | "EXENTO"
    iva_amount: Decimal
    total: Decimal
    product_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "code": self.code,
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "discount": str(self.discount),
            "subtotal": str(self.subtotal),
            "iva_rate": self.iva_rate,
            "iva_amount": str(self.iva_amount),
            "total": str(self.total),
        }

    @classmethod
    def from_dict(cls, d: dict) -> InvoiceLine:
        return cls(
            product_id=d.get("product_id"),
            code=d["code"],
            description=d["description"],
            quantity=Decimal(str(d["quantity"])),
            unit_price=Decimal(str(d["unit_price"])),
            discount=Decimal(str(d["discount"])),
            subtotal=Decimal(str(d["subtotal"])),
            iva_rate=d["iva_rate"],
            iva_amount=Decimal(str(d["iva_amount"])),
            total=Decimal(str(d["total"])),
        )


@dataclass
class Document:
    document_id: str
    tenant_id: str
    doc_type: str
    status: DocumentStatus
    serie: str
    sequential: int
    access_key: str

    client_id: str | None
    buyer_id_type: str
    buyer_id: str
    buyer_name: str
    buyer_email: str | None

    issued_at: date
    sri_environment: str

    subtotal: Decimal
    total_discount: Decimal
    iva_15: Decimal
    iva_5: Decimal
    iva_0: Decimal
    total: Decimal
    payment_method: str

    lines: list[InvoiceLine]

    retry_count: int = 0
    deleted: bool = False
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    created_by: str = ""

    authorization_number: str | None = None
    authorized_at: datetime | None = None
    rejected_at: datetime | None = None
    xml_s3_key: str | None = None
    ride_s3_key: str | None = None
    sri_errors: list[dict] | None = None
    buyer_notification_status: BuyerNotificationStatus | None = None
    buyer_notified_at: datetime | None = None
    buyer_notification_error: str | None = None
    annulled_at: datetime | None = None
    annulled_by: str = ""
    annulment_reason: str | None = None

    # Nota de Credito (doc_type="04") unicamente. FK a la factura acreditada — sus datos
    # se buscan en vivo (nunca cambian post-autorizacion) en vez de duplicarlos aqui.
    related_document_id: str | None = None
    credit_note_reason: str | None = None

    @property
    def sequential_display(self) -> str:
        return f"{self.serie[:3]}-{self.serie[3:]}-{str(self.sequential).zfill(9)}"

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "tenant_id": self.tenant_id,
            "doc_type": self.doc_type,
            "status": self.status.value,
            "serie": self.serie,
            "sequential": self.sequential,
            "sequential_display": self.sequential_display,
            "access_key": self.access_key,
            "client_id": self.client_id,
            "buyer_id_type": self.buyer_id_type,
            "buyer_id": self.buyer_id,
            "buyer_name": self.buyer_name,
            "buyer_email": self.buyer_email,
            "issued_at": self.issued_at.isoformat(),
            "sri_environment": self.sri_environment,
            "subtotal": str(self.subtotal),
            "total_discount": str(self.total_discount),
            "iva_15": str(self.iva_15),
            "iva_5": str(self.iva_5),
            "iva_0": str(self.iva_0),
            "total": str(self.total),
            "payment_method": self.payment_method,
            "lines": [ln.to_dict() for ln in self.lines],
            "retry_count": self.retry_count,
            "authorization_number": self.authorization_number,
            "authorized_at": isoformat_ecuador(self.authorized_at),
            "rejected_at": isoformat_ecuador(self.rejected_at),
            "xml_s3_key": self.xml_s3_key,
            "ride_s3_key": self.ride_s3_key,
            "sri_errors": self.sri_errors,
            "buyer_notification_status": (
                self.buyer_notification_status.value if self.buyer_notification_status else None
            ),
            "buyer_notified_at": (isoformat_ecuador(self.buyer_notified_at)),
            "buyer_notification_error": self.buyer_notification_error,
            "created_at": isoformat_ecuador(self.created_at),
            "updated_at": isoformat_ecuador(self.updated_at),
            "created_by": self.created_by,
            "annulled_at": isoformat_ecuador(self.annulled_at),
            "annulled_by": self.annulled_by,
            "annulment_reason": self.annulment_reason,
            "related_document_id": self.related_document_id,
            "credit_note_reason": self.credit_note_reason,
        }
