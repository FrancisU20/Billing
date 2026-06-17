from __future__ import annotations

from dataclasses import dataclass

from lambdas.subscriptions.domain.entities.payment import PaymentStatus
from lambdas.subscriptions.domain.errors import PaymentNotFoundError
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository

# Map dLocal Go terminal statuses to internal PaymentStatus.
# PENDING/AUTHORIZED are not mapped — we only act on final states.
_TERMINAL_MAP: dict[str, PaymentStatus] = {
    "PAID": "PAID",
    "APPROVED": "PAID",
    "REJECTED": "REJECTED",
    "FAILED": "FAILED",
    "CANCELLED": "CANCELLED",
}


@dataclass(frozen=True)
class ProcessWebhookResult:
    order_id: str
    status: str
    updated: bool


class ProcessWebhookUseCase:
    def __init__(self, payment_repo: IPaymentRepository) -> None:
        self._payment_repo = payment_repo

    def execute(self, order_id: str, dlocal_status: str) -> ProcessWebhookResult:
        try:
            payment = self._payment_repo.get_by_order_id(order_id)
        except PaymentNotFoundError:
            # Unknown order — idempotent no-op (could belong to another integration).
            return ProcessWebhookResult(order_id=order_id, status=dlocal_status, updated=False)

        new_status = _TERMINAL_MAP.get(dlocal_status.upper())
        if not new_status or payment.status == new_status:
            return ProcessWebhookResult(order_id=order_id, status=payment.status, updated=False)

        payment.status = new_status
        self._payment_repo.save(payment)
        return ProcessWebhookResult(order_id=order_id, status=new_status, updated=True)
