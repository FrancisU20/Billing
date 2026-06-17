from __future__ import annotations

from dataclasses import dataclass

from lambdas.tenants.domain.errors import (
    SubscriptionAlreadyActiveError,
    SubscriptionRenewalPaymentAlreadyAppliedError,
    SubscriptionRenewalPaymentNotConfirmedError,
    SubscriptionRenewalPlanMismatchError,
    TenantNotFoundError,
)
from lambdas.tenants.domain.repositories.i_payment_reader import IPaymentReader
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.use_cases.activate_subscription import ActivateSubscriptionUseCase
from shared.errors import OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)

_RECONCILER_USER_ID = "system:pending-activation-reconciler"

_SKIPPABLE_ERRORS = (
    SubscriptionAlreadyActiveError,
    SubscriptionRenewalPaymentAlreadyAppliedError,
    SubscriptionRenewalPaymentNotConfirmedError,
    SubscriptionRenewalPlanMismatchError,
    TenantNotFoundError,
    OptimisticLockError,
)


@dataclass(frozen=True)
class ReconcileResult:
    activated: int
    skipped: int
    errors: int


class PendingActivationReconcilerUseCase:
    def __init__(
        self,
        tenant_repo: ITenantRepository,
        payment_reader: IPaymentReader,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._activate = ActivateSubscriptionUseCase(tenant_repo, payment_reader)

    def execute(self) -> ReconcileResult:
        candidates = self._tenant_repo.list_with_pending_activation()

        activated = skipped = errors = 0

        for tenant in candidates:
            if not tenant.pending_order_id:
                skipped += 1
                continue
            try:
                tenant_entity, result, payment_transact = self._activate.execute(
                    tenant.id, tenant.pending_order_id, _RECONCILER_USER_ID
                )
                self._tenant_repo.commit(
                    tenant=tenant_entity,
                    user_id=_RECONCILER_USER_ID,
                    action="RECONCILE_ACTIVATE_SUBSCRIPTION",
                    events=[],
                    idempotency=None,
                    response=None,
                    extra_transact_items=[payment_transact],
                )
                activated += 1
                _log.info(
                    "pending activation reconciled",
                    tenant_id=tenant.id,
                    order_id=tenant.pending_order_id,
                )
            except _SKIPPABLE_ERRORS as exc:
                _log.warning(
                    "pending activation reconciler skipped tenant",
                    tenant_id=tenant.id,
                    order_id=tenant.pending_order_id,
                    reason=type(exc).__name__,
                )
                skipped += 1
            except Exception:
                _log.error(
                    "pending activation reconciler unexpected error",
                    tenant_id=tenant.id,
                    order_id=tenant.pending_order_id,
                    exc_info=True,
                )
                errors += 1

        return ReconcileResult(activated=activated, skipped=skipped, errors=errors)
