from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PayPalOrderResult:
    order_id: str


@dataclass(frozen=True)
class PayPalCaptureResult:
    order_id: str
    status: str
    payer_id: str
    payer_email: str | None


class IPayPalClient(ABC):
    @abstractmethod
    def create_order(self, amount: str, currency: str) -> PayPalOrderResult: ...

    @abstractmethod
    def capture_order(self, order_id: str) -> PayPalCaptureResult: ...
