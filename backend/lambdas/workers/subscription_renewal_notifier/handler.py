from __future__ import annotations

"""Subscription renewal notifier — invoked daily by an EventBridge scheduled rule.

Scans active tenants whose subscription cycle ends within 7 days or has already expired:
- Ending within 7 days and reminder not yet sent → sends reminder email.
- Already expired with a saved card → attempts automatic renewal charge.
  - PAID → applies renewal, no expiration.
  - REJECTED → marks payment_failed and sends payment failure email.
- Expired with no saved card → expires subscription and sends expiration email.
"""

from datetime import UTC, datetime

from lambdas.subscriptions.infra.dlocal_client import DLocalClient
from lambdas.subscriptions.infra.payment_repository import DynamoPaymentRepository
from lambdas.tenants.infra.plan_catalog import DynamoPlanCatalog
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from lambdas.workers.email_notifications.infra.brevo_email_sender import BrevoEmailSender
from lambdas.workers.subscription_renewal_notifier.use_case import (
    NotifySubscriptionRenewalUseCase,
)
from shared.config import env
from shared.db.client import get_table
from shared.errors import AppError, InternalError
from shared.logger import bind_invocation_context, clear_invocation_context, get_logger
from shared.secrets.client import get_secret_json

_log = get_logger(__name__)

_TENANTS_TABLE = get_table("TENANTS_TABLE")
_AUDIT_TABLE = get_table("AUDIT_LOG_TABLE") if env("AUDIT_LOG_TABLE", "") else None
_PLANS_TABLE = get_table("PLANS_TABLE") if env("PLANS_TABLE", "") else None
_PAYMENTS_TABLE = get_table("PAYMENTS_TABLE") if env("PAYMENTS_TABLE", "") else None
_FRONTEND_URL = env("FRONTEND_URL", "")


def _repo() -> DynamoTenantRepository:
    return DynamoTenantRepository(_TENANTS_TABLE, _AUDIT_TABLE, None)


def _email_sender() -> BrevoEmailSender:
    return BrevoEmailSender()


def _dlocal() -> DLocalClient | None:
    if not env("DLOCALGO_CREDENTIALS_NAME", ""):
        return None
    creds = get_secret_json(env("DLOCALGO_CREDENTIALS_NAME"))
    return DLocalClient(
        base_url=env("DLOCALGO_API_URL"),
        api_key=creds["api_key"],
        secret_key=creds["secret_key"],
    )


def handler(event: dict, context) -> dict:
    clear_invocation_context()
    bind_invocation_context(
        request_id=getattr(context, "aws_request_id", "local"),
        lambda_name=getattr(context, "function_name", "local"),
    )

    dlocal = _dlocal()
    plan_catalog = DynamoPlanCatalog(_PLANS_TABLE) if _PLANS_TABLE and dlocal else None
    payment_repo = DynamoPaymentRepository(_PAYMENTS_TABLE) if _PAYMENTS_TABLE and dlocal else None

    try:
        result = NotifySubscriptionRenewalUseCase(
            _repo(),
            _email_sender(),
            now=datetime.now(UTC),
            frontend_url=_FRONTEND_URL,
            plan_catalog=plan_catalog,
            dlocal=dlocal,
            payment_repo=payment_repo,
        ).execute()
        _log.info(
            "subscription renewal notifications sent",
            reminders_sent=result.reminders_sent,
            expirations_processed=result.expirations_processed,
            auto_charged=result.auto_charged,
            payment_failed_count=result.payment_failed_count,
        )
        return {
            "remindersSent": result.reminders_sent,
            "expirationsProcessed": result.expirations_processed,
            "autoCharged": result.auto_charged,
            "paymentFailedCount": result.payment_failed_count,
        }
    except AppError:
        _log.warning("subscription renewal notifier application error", exc_info=True)
        raise
    except Exception as exc:
        _log.error("subscription renewal notifier unexpected error", exc_info=True)
        raise InternalError() from exc
