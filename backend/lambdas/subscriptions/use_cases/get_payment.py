from __future__ import annotations

from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository


class GetPaymentUseCase:
    def __init__(self, payment_repo: IPaymentRepository) -> None:
        self._payments = payment_repo

    def execute(self, order_id: str) -> dict:
        payment = self._payments.get_by_order_id(order_id)
        return payment.to_dict()
