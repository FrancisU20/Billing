from __future__ import annotations

import hmac

from lambdas.subscriptions.domain.errors import PaymentAccessDeniedError
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository


class GetPaymentUseCase:
    def __init__(self, payment_repo: IPaymentRepository) -> None:
        self._payments = payment_repo

    def execute(self, order_id: str, checkout_token: str) -> dict:
        payment = self._payments.get_by_order_id(order_id)
        if not payment.checkout_token or not hmac.compare_digest(
            payment.checkout_token,
            checkout_token,
        ):
            raise PaymentAccessDeniedError()

        data = payment.to_dict()
        return {
            "order_id": data["order_id"],
            "tenant_id": data["tenant_id"],
            "plan_id": data["plan_id"],
            "plan_cycle": data["plan_cycle"],
            "amount": data["amount"],
            "currency": data["currency"],
            "status": data["status"],
            "created_at": data["created_at"],
            "confirmed_at": data["confirmed_at"],
        }
