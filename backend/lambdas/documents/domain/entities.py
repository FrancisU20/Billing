from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum


def _now() -> datetime:
    return datetime.now(UTC)


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    AUTHORIZED = "AUTHORIZED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    FAILED_PERMANENT = "FAILED_PERMANENT"


class BuyerNotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    SKIPPED_NO_EMAIL = "SKIPPED_NO_EMAIL"
    FAILED = "FAILED"


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

    def to_dict(self) -> dict:
        return {
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
            "authorized_at": self.authorized_at.isoformat() if self.authorized_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "xml_s3_key": self.xml_s3_key,
            "ride_s3_key": self.ride_s3_key,
            "sri_errors": self.sri_errors,
            "buyer_notification_status": (
                self.buyer_notification_status.value if self.buyer_notification_status else None
            ),
            "buyer_notified_at": (
                self.buyer_notified_at.isoformat() if self.buyer_notified_at else None
            ),
            "buyer_notification_error": self.buyer_notification_error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
        }
