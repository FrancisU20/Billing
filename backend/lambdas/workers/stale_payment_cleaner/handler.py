from __future__ import annotations

"""Stale payment cleaner — invoked hourly by EventBridge.

Cancels local CREATED/PENDING subscription payments older than the configured grace window.
The update is conditional, so a late webhook or manual flow that already moved the payment
out of an open state is not overwritten.
"""

from datetime import UTC, datetime

from lambdas.subscriptions.infra.payment_repository import DynamoPaymentRepository
from lambdas.workers.stale_payment_cleaner.use_case import CleanStalePaymentsUseCase
from shared.config import env
from shared.db.client import get_table
from shared.errors import AppError, InternalError
from shared.logger import bind_invocation_context, clear_invocation_context, get_logger

_log = get_logger(__name__)

_PAYMENTS_TABLE = get_table("PAYMENTS_TABLE")
_GRACE_MINUTES = int(env("STALE_PAYMENT_GRACE_MINUTES", "1440"))


def handler(event: dict, context) -> dict:
    clear_invocation_context()
    bind_invocation_context(
        request_id=getattr(context, "aws_request_id", "local"),
        lambda_name=getattr(context, "function_name", "local"),
    )

    try:
        result = CleanStalePaymentsUseCase(
            DynamoPaymentRepository(_PAYMENTS_TABLE),
            now=datetime.now(UTC),
            grace_minutes=_GRACE_MINUTES,
        ).execute()
        _log.info(
            "stale payment cleaner finished",
            candidates=result.candidates,
            cancelled=result.cancelled,
            skipped=result.skipped,
            errors=result.errors,
        )
        return {
            "candidates": result.candidates,
            "cancelled": result.cancelled,
            "skipped": result.skipped,
            "errors": result.errors,
        }
    except AppError:
        _log.warning("stale payment cleaner application error", exc_info=True)
        raise
    except Exception as exc:
        _log.error("stale payment cleaner unexpected error", exc_info=True)
        raise InternalError() from exc
