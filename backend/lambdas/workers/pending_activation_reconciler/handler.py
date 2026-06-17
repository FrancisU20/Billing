from __future__ import annotations

"""Pending-activation reconciler — invoked every 5 minutes by an EventBridge rule.

Scans tenants with subscription_status='pending_payment' that have a pending_order_id
written by the activate_subscription use case (Phase 1 pre-save). For each, retries the
full activation transaction. Handles cases where the browser session was lost after the
dLocal payment confirmed but before the activate API call completed or committed.
"""

from lambdas.tenants.infra.payment_reader import DynamoPaymentReader
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from lambdas.workers.pending_activation_reconciler.use_case import (
    PendingActivationReconcilerUseCase,
)
from shared.db.client import get_table
from shared.errors import AppError, InternalError
from shared.logger import bind_invocation_context, clear_invocation_context, get_logger

_log = get_logger(__name__)

_TENANTS_TABLE = get_table("TENANTS_TABLE")
_PAYMENTS_TABLE = get_table("PAYMENTS_TABLE")
_AUDIT_TABLE = get_table("AUDIT_LOG_TABLE")


def _use_case() -> PendingActivationReconcilerUseCase:
    repo = DynamoTenantRepository(_TENANTS_TABLE, _AUDIT_TABLE, None)
    payment_reader = DynamoPaymentReader(_PAYMENTS_TABLE)
    return PendingActivationReconcilerUseCase(repo, payment_reader)


def handler(event: dict, context) -> dict:
    clear_invocation_context()
    bind_invocation_context(
        request_id=getattr(context, "aws_request_id", "local"),
        lambda_name=getattr(context, "function_name", "local"),
    )

    try:
        result = _use_case().execute()
        _log.info(
            "pending activation reconciler finished",
            activated=result.activated,
            skipped=result.skipped,
            errors=result.errors,
        )
        return {
            "activated": result.activated,
            "skipped": result.skipped,
            "errors": result.errors,
        }
    except AppError:
        _log.warning("pending activation reconciler application error", exc_info=True)
        raise
    except Exception as exc:
        _log.error("pending activation reconciler unexpected error", exc_info=True)
        raise InternalError() from exc
