from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CreatePaymentCommand:
    plan_id: str
    currency: str = "USD"


@dataclass
class CapturePaymentCommand:
    order_id: str
