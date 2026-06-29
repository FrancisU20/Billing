from __future__ import annotations

import urllib.error
from dataclasses import dataclass

from lambdas.subscriptions.domain.errors import PaymentNotRefundableError, PaymentRefundError
from lambdas.subscriptions.domain.repositories.i_dlocal_client import IDLocalClient
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository
from shared.logger import get_logger

_log = get_logger(__name__)

_REFUNDABLE_STATUSES = {"PAID", "AUTHORIZED"}


@dataclass(frozen=True)
class RefundPaymentResult:
    order_id: str
    refund_id: str
    status: str


class RefundPaymentUseCase:
    def __init__(self, payment_repo: IPaymentRepository, dlocal: IDLocalClient) -> None:
        self._payment_repo = payment_repo
        self._dlocal = dlocal

    def execute(self, order_id: str) -> RefundPaymentResult:
        payment = self._payment_repo.get_by_order_id(order_id)
        if payment.status not in _REFUNDABLE_STATUSES:
            raise PaymentNotRefundableError()

        try:
            result = self._dlocal.refund_payment(order_id, payment.amount, payment.currency)
        except urllib.error.HTTPError as exc:
            _log.error(
                "dLocal refund failed",
                order_id=order_id,
                status=exc.code,
                error=str(exc),
            )
            raise PaymentRefundError() from exc
        except urllib.error.URLError as exc:
            _log.error(
                "dLocal refund failed",
                order_id=order_id,
                reason=str(exc.reason),
                error=str(exc),
            )
            raise PaymentRefundError() from exc
        except Exception as exc:
            _log.error(
                "dLocal refund failed unexpectedly",
                order_id=order_id,
                error=str(exc),
                exc_info=True,
            )
            raise PaymentRefundError() from exc

        payment.refund()
        self._payment_repo.save(payment)

        return RefundPaymentResult(
            order_id=order_id,
            refund_id=result.refund_id,
            status=result.status,
        )
