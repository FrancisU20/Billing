from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CreatePaymentCommand:
    plan_id: str
    currency: str = "USD"


@dataclass
class ConfirmPaymentCommand:
    order_id: str
    card_token: str
    payer_name: str
    payer_email: str
    payer_document: str
