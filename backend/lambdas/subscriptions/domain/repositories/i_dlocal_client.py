from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DLocalCreatePaymentResult:
    payment_id: str
    checkout_token: str


@dataclass(frozen=True)
class DLocalConfirmPaymentResult:
    payment_id: str
    status: str
    payer_id: str | None
    payer_email: str | None


class IDLocalClient(ABC):
    @abstractmethod
    def create_payment(
        self, amount: str, currency: str, country: str
    ) -> DLocalCreatePaymentResult: ...

    @abstractmethod
    def confirm_payment(
        self,
        checkout_token: str,
        card_token: str,
        payer_name: str,
        payer_email: str,
        payer_document: str,
    ) -> DLocalConfirmPaymentResult: ...
