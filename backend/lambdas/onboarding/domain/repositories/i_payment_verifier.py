from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CapturedPaymentInfo:
    order_id: str
    payer_id: str
    payer_email: str | None
    plan_id: str
    amount: str
    plan_cycle: str


class IPaymentVerifier(ABC):
    @abstractmethod
    def get_captured_payment(self, order_id: str) -> CapturedPaymentInfo:
        """Return payment info only if status is CAPTURED.

        Raises OnboardingPaymentNotFoundError if order_id does not exist.
        Raises OnboardingPaymentNotCapturedError if status is not CAPTURED.
        """
