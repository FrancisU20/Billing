from __future__ import annotations

import urllib.error
from dataclasses import dataclass

from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.repositories.i_dlocal_client import IDLocalClient
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository
from lambdas.subscriptions.domain.repositories.i_plan_catalog import IPlanCatalog
from lambdas.tenants.domain.errors import (
    NoSavedPaymentMethodError,
    RetryPaymentNotEligibleError,
    SavedCardRejectedError,
)
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.billing import gross_price
from shared.dates import isoformat_ecuador, now_utc
from shared.logger import get_logger

_log = get_logger(__name__)

_COUNTRY = "EC"
_CURRENCY = "USD"
_ELIGIBLE_STATUSES = {"payment_failed", "expired"}


@dataclass(frozen=True)
class RetryPaymentResult:
    tenant_id: str
    plan_cycle_ends_at: str
    subscription_status: str


class RetryPaymentUseCase:
    def __init__(
        self,
        tenant_repo: ITenantRepository,
        plan_catalog: IPlanCatalog,
        dlocal: IDLocalClient,
        payment_repo: IPaymentRepository,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._plans = plan_catalog
        self._dlocal = dlocal
        self._payments = payment_repo

    def execute(self, tenant_id: str, updated_by: str) -> tuple[Tenant, RetryPaymentResult, dict]:
        tenant = self._tenant_repo.get_by_id(tenant_id)

        if not tenant.dlocal_payer_id:
            raise NoSavedPaymentMethodError()

        if tenant.subscription_status not in _ELIGIBLE_STATUSES:
            raise RetryPaymentNotEligibleError()

        plan = self._plans.get(tenant.plan_id)
        billing_cycle = tenant.billing_cycle
        price = plan.annual_price if billing_cycle == "year" else plan.monthly_price
        net = f"{price:.2f}"
        amount = gross_price(net)

        try:
            charge = self._dlocal.charge_saved_payer(
                tenant.dlocal_payer_id, amount, _CURRENCY, _COUNTRY
            )
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            _log.error("retry-payment dLocal call failed", tenant_id=tenant_id, error=str(exc))
            raise SavedCardRejectedError() from exc

        if charge.status != "PAID":
            _log.warning(
                "retry-payment card rejected",
                tenant_id=tenant_id,
                dlocal_status=charge.status,
            )
            raise SavedCardRejectedError()

        now = now_utc()
        payment = Payment(
            order_id=charge.payment_id,
            tenant_id=tenant_id,
            plan_id=tenant.plan_id,
            amount=amount,
            currency=_CURRENCY,
            status="PAID",
            plan_cycle=billing_cycle,
            confirmed_at=now,
            payer_id=tenant.dlocal_payer_id,
        )
        payment_transact = self._payments.save_transact_item(payment)

        tenant.apply_subscription_renewal(
            payer_id=tenant.dlocal_payer_id,
            plan_cycle=billing_cycle,
            now=now,
            updated_by=updated_by,
        )

        _log.info(
            "retry-payment succeeded",
            tenant_id=tenant_id,
            order_id=charge.payment_id,
            amount=amount,
        )

        return (
            tenant,
            RetryPaymentResult(
                tenant_id=tenant_id,
                plan_cycle_ends_at=isoformat_ecuador(tenant.plan_cycle_ends_at) or "",
                subscription_status=tenant.subscription_status or "active",
            ),
            payment_transact,
        )
