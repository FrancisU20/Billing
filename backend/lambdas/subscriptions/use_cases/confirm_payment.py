from __future__ import annotations

import urllib.error
from dataclasses import dataclass

from lambdas.subscriptions.domain.commands import ConfirmPaymentCommand
from lambdas.subscriptions.domain.errors import (
    PaymentAlreadyConfirmedError,
    PaymentConfirmError,
)
from lambdas.subscriptions.domain.repositories.i_dlocal_client import IDLocalClient
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository
from shared.logger import get_logger

_log = get_logger(__name__)

_PAID_STATUSES = frozenset({"PAID", "AUTHORIZED"})


@dataclass
class ConfirmPaymentResult:
    order_id: str
    status: str
    payer_id: str | None
    payer_email: str | None
    redirect_url: str | None = None


class ConfirmPaymentUseCase:
    def __init__(self, dlocal: IDLocalClient, payment_repo: IPaymentRepository) -> None:
        self._dlocal = dlocal
        self._payments = payment_repo

    def execute(self, cmd: ConfirmPaymentCommand) -> ConfirmPaymentResult:
        payment = self._payments.get_by_order_id(cmd.order_id)

        if payment.status == "PAID":
            raise PaymentAlreadyConfirmedError()

        if not payment.checkout_token:
            raise PaymentConfirmError()

        try:
            result = self._dlocal.confirm_payment(
                payment.checkout_token,
                cmd.card_token,
                cmd.client_first_name,
                cmd.client_last_name,
                cmd.client_email,
                cmd.client_document_type,
                cmd.client_document,
            )
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            detail = str(exc.code) if isinstance(exc, urllib.error.HTTPError) else str(exc.reason)
            _log.error("dLocal confirm failed", order_id=cmd.order_id, error=detail)
            payment.fail(f"dLocal error: {detail}")
            self._payments.save(payment)
            raise PaymentConfirmError() from exc

        if result.status in _PAID_STATUSES:
            payment.confirm(result.payer_id, result.payer_email)
        elif result.status == "PENDING":
            payment.mark_pending("dLocal requires customer action")
        else:
            payment.fail(f"dLocal status: {result.status}")

        self._payments.save(payment)

        return ConfirmPaymentResult(
            order_id=payment.order_id,
            status=payment.status,
            payer_id=payment.payer_id,
            payer_email=payment.payer_email,
            redirect_url=result.redirect_url,
        )
