from __future__ import annotations

from botocore.exceptions import ClientError

from lambdas.onboarding.domain.errors import (
    OnboardingPaymentNotCapturedError,
    OnboardingPaymentNotFoundError,
)
from lambdas.onboarding.domain.repositories.i_payment_verifier import (
    CapturedPaymentInfo,
    IPaymentVerifier,
)
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoPaymentVerifier(IPaymentVerifier):
    def __init__(self, payments_table) -> None:
        self._table = payments_table

    def get_captured_payment(self, order_id: str) -> CapturedPaymentInfo:
        try:
            resp = self._table.get_item(Key={"id": f"PAYMENT#{order_id}"})
        except ClientError as exc:
            _log.error("DynamoDB get_item error (payment verifier)", error=str(exc))
            raise DatabaseError() from exc

        item = resp.get("Item")
        if not item:
            raise OnboardingPaymentNotFoundError()

        if item.get("status") != "CAPTURED":
            raise OnboardingPaymentNotCapturedError()

        return CapturedPaymentInfo(
            order_id=item.get("order_id", ""),
            payer_id=item.get("payer_id", ""),
            payer_email=item.get("payer_email"),
            plan_id=item.get("plan_id", ""),
            amount=item.get("amount", "0.00"),
            plan_cycle=item.get("plan_cycle", "month"),
        )
