from __future__ import annotations

"""Orphan payment notifier — invocado por EventBridge cada hora.

Escanea la tabla payments buscando pagos PAID con tenant_id ausente
que superaron el grace period (default 30 min) y notifica al superadmin.
"""

from datetime import UTC, datetime, timedelta

from boto3.dynamodb.conditions import Attr

from lambdas.workers.email_notifications.infra.brevo_email_sender import BrevoEmailSender
from lambdas.workers.orphan_payment_notifier.use_case import (
    IOrphanPaymentQuery,
    NotifyOrphanPaymentsUseCase,
    OrphanPaymentSummary,
)
from shared.config import env
from shared.db.client import get_table
from shared.errors import AppError, InternalError
from shared.logger import bind_invocation_context, clear_invocation_context, get_logger

_log = get_logger(__name__)

_PAYMENTS_TABLE = get_table("PAYMENTS_TABLE")
_SUPERADMIN_EMAIL = env("SUPERADMIN_EMAIL")
_GRACE_MINUTES = int(env("ORPHAN_PAYMENT_GRACE_MINUTES", "30"))


class _DynamoOrphanPaymentQuery(IOrphanPaymentQuery):
    """Scan payments with status=PAID, no tenant_id, confirmed before cutoff."""

    def __init__(self, table) -> None:
        self._table = table

    def list_orphaned_paid(self, *, cutoff: datetime) -> list[OrphanPaymentSummary]:
        cutoff_iso = cutoff.isoformat()
        results: list[OrphanPaymentSummary] = []
        scan_kwargs: dict = {
            "FilterExpression": (
                Attr("status").eq("PAID")
                & Attr("tenant_id").not_exists()
                & Attr("confirmed_at").lte(cutoff_iso)
            ),
            "ProjectionExpression": (
                "order_id, payer_email, plan_id, amount, currency, confirmed_at"
            ),
        }

        while True:
            resp = self._table.scan(**scan_kwargs)
            for item in resp.get("Items", []):
                results.append(
                    OrphanPaymentSummary(
                        order_id=item.get("order_id", ""),
                        payer_email=item.get("payer_email"),
                        plan_id=item.get("plan_id", ""),
                        amount=item.get("amount", "0.00"),
                        currency=item.get("currency", "USD"),
                        confirmed_at=item.get("confirmed_at", ""),
                    )
                )
            last_key = resp.get("LastEvaluatedKey")
            if not last_key:
                break
            scan_kwargs["ExclusiveStartKey"] = last_key

        return results


def handler(event: dict, context) -> dict:
    clear_invocation_context()
    bind_invocation_context(
        request_id=getattr(context, "aws_request_id", "local"),
        lambda_name=getattr(context, "function_name", "local"),
    )

    try:
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=_GRACE_MINUTES)

        result = NotifyOrphanPaymentsUseCase(
            _DynamoOrphanPaymentQuery(_PAYMENTS_TABLE),
            BrevoEmailSender(),
            superadmin_email=_SUPERADMIN_EMAIL,
            now=cutoff,
        ).execute()

        _log.info("orphan payment notifier finished", alerts_sent=result.alerts_sent)
        return {"alertsSent": result.alerts_sent}

    except AppError:
        _log.warning("orphan payment notifier application error", exc_info=True)
        raise
    except Exception as exc:
        _log.error("orphan payment notifier unexpected error", exc_info=True)
        raise InternalError() from exc
