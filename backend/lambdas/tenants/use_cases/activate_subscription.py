from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from lambdas.tenants.domain.errors import (
    SubscriptionAlreadyActiveError,
    SubscriptionRenewalPaymentAlreadyAppliedError,
    SubscriptionRenewalPaymentNotConfirmedError,
    SubscriptionRenewalPlanMismatchError,
    TenantNotFoundError,
)
from lambdas.tenants.domain.repositories.i_payment_reader import IPaymentReader
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository

_PAID_STATUSES = frozenset({"PAID", "AUTHORIZED"})


@dataclass(frozen=True)
class ActivateSubscriptionResult:
    tenant_id: str
    plan_cycle_ends_at: str
    subscription_status: str


class ActivateSubscriptionUseCase:
    def __init__(
        self,
        tenant_repo: ITenantRepository,
        payment_reader: IPaymentReader,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._payment_reader = payment_reader

    def execute(self, tenant_id: str, order_id: str, updated_by: str):
        tenant = self._tenant_repo.get_by_id(tenant_id)
        if tenant.deleted:
            raise TenantNotFoundError()

        if tenant.subscription_status == "active":
            raise SubscriptionAlreadyActiveError()

        payment = self._payment_reader.get_by_order_id(order_id)

        if payment.status not in _PAID_STATUSES:
            raise SubscriptionRenewalPaymentNotConfirmedError()

        if payment.tenant_id not in ("", tenant_id):
            raise SubscriptionRenewalPaymentAlreadyAppliedError()

        if payment.plan_id != tenant.plan_id:
            raise SubscriptionRenewalPlanMismatchError()

        now = datetime.now(UTC)
        tenant.activate_subscription(
            payer_id=payment.payer_id,
            plan_cycle=payment.plan_cycle,
            now=now,
            updated_by=updated_by,
        )

        payment_transact = self._payment_reader.mark_applied_to_tenant(order_id, tenant_id)

        result = ActivateSubscriptionResult(
            tenant_id=tenant.id,
            plan_cycle_ends_at=tenant.plan_cycle_ends_at.isoformat(),
            subscription_status=tenant.subscription_status or "active",
        )
        return tenant, result, payment_transact
