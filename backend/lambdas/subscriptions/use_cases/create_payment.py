from __future__ import annotations

import urllib.error
from dataclasses import dataclass
from decimal import Decimal

from lambdas.subscriptions.domain.commands import CreatePaymentCommand
from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.errors import FreePlanPaymentError, PaymentCreationError
from lambdas.subscriptions.domain.repositories.i_dlocal_client import IDLocalClient
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository
from lambdas.subscriptions.domain.repositories.i_plan_catalog import IPlanCatalog
from shared.billing import gross_price, markup_display_pct
from shared.logger import get_logger

_log = get_logger(__name__)

_COUNTRY = "EC"


@dataclass
class CreatePaymentResult:
    order_id: str
    checkout_token: str
    amount: str  # gross — what the client is charged
    currency: str
    net_amount: str  # plan base price before markup
    markup_pct: str  # e.g. "12"


class CreatePaymentUseCase:
    def __init__(
        self,
        plan_catalog: IPlanCatalog,
        dlocal: IDLocalClient,
        payment_repo: IPaymentRepository,
    ) -> None:
        self._plans = plan_catalog
        self._dlocal = dlocal
        self._payments = payment_repo

    def execute(self, cmd: CreatePaymentCommand) -> CreatePaymentResult:
        plan = self._plans.get(cmd.plan_id)

        if plan.is_free:
            raise FreePlanPaymentError()

        net_amount = _plan_price(plan.monthly_price, plan.annual_price, plan.limit_cycle)
        amount = gross_price(net_amount)

        try:
            result = self._dlocal.create_payment(amount, cmd.currency, _COUNTRY)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            _log.error("dLocal create payment failed", error=str(exc))
            raise PaymentCreationError() from exc

        payment = Payment(
            order_id=result.payment_id,
            tenant_id=None,
            plan_id=cmd.plan_id,
            amount=amount,
            currency=cmd.currency,
            status="CREATED",
            plan_cycle=plan.limit_cycle,
            checkout_token=result.checkout_token,
        )
        self._payments.save(payment)

        return CreatePaymentResult(
            order_id=result.payment_id,
            checkout_token=result.checkout_token,
            amount=amount,
            currency=cmd.currency,
            net_amount=net_amount,
            markup_pct=markup_display_pct(),
        )


def _plan_price(monthly: Decimal, annual: Decimal, limit_cycle: str) -> str:
    price = annual if limit_cycle == "year" else monthly
    return f"{price:.2f}"
