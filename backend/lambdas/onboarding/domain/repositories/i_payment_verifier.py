from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfirmedPaymentInfo:
    order_id: str
    payer_id: str
    payer_email: str | None
    plan_id: str
    amount: str
    plan_cycle: str


class IPaymentVerifier(ABC):
    @abstractmethod
    def get_confirmed_payment(self, order_id: str) -> ConfirmedPaymentInfo:
        """Return payment info only if status is PAID or AUTHORIZED.

        Raises OnboardingPaymentNotFoundError if order_id does not exist.
        Raises OnboardingPaymentNotConfirmedError if payment has not been confirmed.
        """
