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
    client_first_name: str
    client_last_name: str
    client_email: str
    client_document_type: str
    client_document: str
