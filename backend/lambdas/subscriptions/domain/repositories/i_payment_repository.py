from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from lambdas.subscriptions.domain.entities.payment import Payment, PaymentStatus


class IPaymentRepository(ABC):
    @abstractmethod
    def save(self, payment: Payment) -> None: ...

    @abstractmethod
    def save_transact_item(self, payment: Payment) -> dict: ...

    @abstractmethod
    def get_by_order_id(self, order_id: str) -> Payment: ...

    @abstractmethod
    def link_tenant(self, order_id: str, tenant_id: str) -> None: ...

    @abstractmethod
    def apply_webhook_status(
        self, order_id: str, new_status: PaymentStatus
    ) -> tuple[PaymentStatus, bool]: ...

    @abstractmethod
    def list_stale_open_payments(self, *, cutoff: datetime) -> list[Payment]: ...

    @abstractmethod
    def cancel_stale_open_payment(self, *, order_id: str, cutoff: datetime) -> bool: ...

    @abstractmethod
    def create_auto_renewal_reconciliation_marker(
        self,
        *,
        tenant_id: str,
        cycle_ends_at: datetime,
        plan_id: str,
        amount: str,
        currency: str,
        reason: str,
    ) -> bool: ...

    @abstractmethod
    def save_auto_renewal_reconciliation_marker(
        self,
        payment: Payment,
        *,
        tenant_id: str,
        cycle_ends_at: datetime,
        reason: str,
    ) -> None: ...

    @abstractmethod
    def delete_auto_renewal_reconciliation_marker(
        self, *, tenant_id: str, cycle_ends_at: datetime
    ) -> None: ...
