from __future__ import annotations

from lambdas.subscriptions.domain.entities.payment import PAID_STATUSES
from lambdas.tenants.domain.enums import SubscriptionStatus
from lambdas.tenants.domain.errors import (
    SubscriptionAlreadyActiveError,
    SubscriptionRenewalPaymentAlreadyAppliedError,
    SubscriptionRenewalPaymentNotConfirmedError,
    SubscriptionRenewalPlanMismatchError,
    TenantNotFoundError,
)
from lambdas.tenants.domain.repositories.i_payment_reader import IPaymentReader
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.subscription_result import SubscriptionActivationResult
from shared.dates import isoformat_ecuador, now_utc


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

        if tenant.subscription_status == SubscriptionStatus.ACTIVE:
            raise SubscriptionAlreadyActiveError()

        payment = self._payment_reader.get_by_order_id(order_id)

        if payment.status not in PAID_STATUSES:
            raise SubscriptionRenewalPaymentNotConfirmedError()

        if payment.tenant_id not in ("", tenant_id):
            raise SubscriptionRenewalPaymentAlreadyAppliedError()

        if payment.plan_id != tenant.plan_id:
            raise SubscriptionRenewalPlanMismatchError()

        # Phase 1: bookmark the order on the tenant BEFORE the full transaction.
        # If the commit below fails the order_id survives on DynamoDB, letting the
        # reconciler worker retry without needing the browser session.
        self._tenant_repo.set_pending_order_id(tenant_id, order_id)

        now = now_utc()
        tenant.activate_subscription(
            payer_id=payment.payer_id,
            plan_cycle=payment.plan_cycle,
            now=now,
            updated_by=updated_by,
        )

        payment_transact = self._payment_reader.mark_applied_to_tenant(order_id, tenant_id)

        result = SubscriptionActivationResult(
            tenant_id=tenant.id,
            plan_cycle_ends_at=isoformat_ecuador(tenant.plan_cycle_ends_at) or "",
            subscription_status=(tenant.subscription_status or SubscriptionStatus.ACTIVE).value,
        )
        return tenant, result, payment_transact
