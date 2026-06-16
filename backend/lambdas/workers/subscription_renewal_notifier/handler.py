from __future__ import annotations

"""Subscription renewal notifier — invoked daily by an EventBridge scheduled rule.

Scans active tenants whose subscription cycle ends within 7 days or has already
expired:
- Ending within 7 days and reminder not yet sent → sends renewal reminder email
  and marks `subscription_renewal_reminder_sent_at`.
- Already expired → calls `tenant.expire_subscription()` (suspends account) and
  sends an expiration notice email.
"""

from datetime import UTC, datetime

from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from lambdas.workers.email_notifications.infra.brevo_email_sender import BrevoEmailSender
from lambdas.workers.subscription_renewal_notifier.use_case import (
    NotifySubscriptionRenewalUseCase,
)
from shared.config import env
from shared.db.client import get_table
from shared.errors import AppError, InternalError
from shared.logger import bind_invocation_context, clear_invocation_context, get_logger

_log = get_logger(__name__)

_TENANTS_TABLE = get_table("TENANTS_TABLE")
_AUDIT_TABLE = get_table("AUDIT_LOG_TABLE") if env("AUDIT_LOG_TABLE", "") else None


def _repo() -> DynamoTenantRepository:
    return DynamoTenantRepository(_TENANTS_TABLE, _AUDIT_TABLE, None)


def _email_sender() -> BrevoEmailSender:
    return BrevoEmailSender()


def handler(event: dict, context) -> dict:
    clear_invocation_context()
    bind_invocation_context(
        request_id=getattr(context, "aws_request_id", "local"),
        lambda_name=getattr(context, "function_name", "local"),
    )

    try:
        result = NotifySubscriptionRenewalUseCase(
            _repo(), _email_sender(), now=datetime.now(UTC)
        ).execute()
        _log.info(
            "subscription renewal notifications sent",
            reminders_sent=result.reminders_sent,
            expirations_processed=result.expirations_processed,
        )
        return {
            "remindersSent": result.reminders_sent,
            "expirationsProcessed": result.expirations_processed,
        }
    except AppError:
        _log.warning("subscription renewal notifier application error", exc_info=True)
        raise
    except Exception as exc:
        _log.error("subscription renewal notifier unexpected error", exc_info=True)
        raise InternalError() from exc
