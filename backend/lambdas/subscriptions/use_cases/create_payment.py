from __future__ import annotations

import urllib.error
from dataclasses import dataclass
from decimal import Decimal

from lambdas.subscriptions.domain.commands import CreatePaymentCommand
from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.errors import FreePlanPaymentError, PaymentCreationError
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository
from lambdas.subscriptions.domain.repositories.i_paypal_client import IPayPalClient
from lambdas.subscriptions.domain.repositories.i_plan_catalog import IPlanCatalog
from shared.logger import get_logger

_log = get_logger(__name__)


@dataclass
class CreatePaymentResult:
    order_id: str
    amount: str
    currency: str


class CreatePaymentUseCase:
    def __init__(
        self,
        plan_catalog: IPlanCatalog,
        paypal: IPayPalClient,
        payment_repo: IPaymentRepository,
    ) -> None:
        self._plans = plan_catalog
        self._paypal = paypal
        self._payments = payment_repo

    def execute(self, cmd: CreatePaymentCommand) -> CreatePaymentResult:
        plan = self._plans.get(cmd.plan_id)

        if plan.is_free:
            raise FreePlanPaymentError()

        amount = _plan_price(plan.monthly_price, plan.annual_price, plan.limit_cycle)

        try:
            order = self._paypal.create_order(amount, cmd.currency)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            _log.error("PayPal create order failed", error=str(exc))
            raise PaymentCreationError() from exc

        payment = Payment(
            order_id=order.order_id,
            tenant_id=None,
            plan_id=cmd.plan_id,
            amount=amount,
            currency=cmd.currency,
            status="CREATED",
            plan_cycle=plan.limit_cycle,
        )
        self._payments.save(payment)

        return CreatePaymentResult(
            order_id=order.order_id,
            amount=amount,
            currency=cmd.currency,
        )


def _plan_price(monthly: Decimal, annual: Decimal, limit_cycle: str) -> str:
    price = annual if limit_cycle == "year" else monthly
    return f"{price:.2f}"
