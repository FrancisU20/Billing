from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

PaymentStatus = Literal["CREATED", "PENDING", "PAID", "REJECTED", "CANCELLED", "FAILED"]


@dataclass
class Payment:
    order_id: str
    tenant_id: str | None
    plan_id: str
    amount: str
    currency: str
    status: PaymentStatus
    plan_cycle: str = "month"
    checkout_token: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    confirmed_at: datetime | None = None
    payer_id: str | None = None
    payer_email: str | None = None
    error_detail: str | None = None

    def confirm(self, payer_id: str | None, payer_email: str | None) -> None:
        self.status = "PAID"
        self.confirmed_at = datetime.now(UTC)
        self.payer_id = payer_id
        self.payer_email = payer_email

    def mark_pending(self, detail: str | None = None) -> None:
        self.status = "PENDING"
        self.error_detail = detail

    def fail(self, detail: str) -> None:
        self.status = "FAILED"
        self.error_detail = detail

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "tenant_id": self.tenant_id,
            "plan_id": self.plan_id,
            "plan_cycle": self.plan_cycle,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "payer_id": self.payer_id,
            "payer_email": self.payer_email,
        }
