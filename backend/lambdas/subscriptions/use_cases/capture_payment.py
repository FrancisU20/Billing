from __future__ import annotations

import urllib.error
from dataclasses import dataclass

from lambdas.subscriptions.domain.commands import CapturePaymentCommand
from lambdas.subscriptions.domain.errors import PaymentAlreadyCapturedError, PaymentCaptureError
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository
from lambdas.subscriptions.domain.repositories.i_paypal_client import IPayPalClient
from shared.logger import get_logger

_log = get_logger(__name__)


@dataclass
class CapturePaymentResult:
    order_id: str
    status: str
    payer_id: str
    payer_email: str | None


class CapturePaymentUseCase:
    def __init__(self, paypal: IPayPalClient, payment_repo: IPaymentRepository) -> None:
        self._paypal = paypal
        self._payments = payment_repo

    def execute(self, cmd: CapturePaymentCommand) -> CapturePaymentResult:
        payment = self._payments.get_by_order_id(cmd.order_id)

        if payment.status == "CAPTURED":
            raise PaymentAlreadyCapturedError()

        try:
            result = self._paypal.capture_order(cmd.order_id)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            detail = str(exc.code) if isinstance(exc, urllib.error.HTTPError) else str(exc.reason)
            _log.error("PayPal capture failed", order_id=cmd.order_id, error=detail)
            payment.fail(f"PayPal error: {detail}")
            self._payments.save(payment)
            raise PaymentCaptureError() from exc

        payment.capture(result.payer_id, result.payer_email)
        self._payments.save(payment)

        return CapturePaymentResult(
            order_id=payment.order_id,
            status=payment.status,
            payer_id=result.payer_id,
            payer_email=result.payer_email,
        )
