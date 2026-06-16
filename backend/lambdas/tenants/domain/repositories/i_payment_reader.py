from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentRecord:
    order_id: str
    tenant_id: str
    plan_id: str
    amount: str
    status: str
    plan_cycle: str
    payer_id: str


class IPaymentReader(ABC):
    @abstractmethod
    def get_by_order_id(self, order_id: str) -> PaymentRecord:
        """Raises SubscriptionRenewalPaymentNotFoundError if not found."""

    @abstractmethod
    def mark_applied_to_tenant(self, order_id: str, tenant_id: str) -> dict:
        """Return a transact_item dict that sets tenant_id on the payment.

        Must be included as an extra_transact_item in the tenant commit to ensure
        atomicity — one payment cannot be applied to two different tenants.
        """
