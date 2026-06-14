from __future__ import annotations

"""Certificate expiry notifier — invoked daily by an EventBridge scheduled rule.

Scans `tenants` for active/suspended tenants whose certificate expires within
60 or 30 days and sends a reminder email via Brevo for each threshold not yet
notified. Idempotency across days is tracked on the tenant itself
(`cert_expiry_alert_60_sent_at` / `cert_expiry_alert_30_sent_at`), reset whenever
a new certificate is uploaded.
"""

from datetime import UTC, datetime

from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from lambdas.workers.certificate_expiry_notifier.use_case import (
    NotifyCertificateExpiryUseCase,
)
from lambdas.workers.email_notifications.infra.brevo_email_sender import BrevoEmailSender
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
        result = NotifyCertificateExpiryUseCase(
            _repo(), _email_sender(), now=datetime.now(UTC)
        ).execute()
        _log.info(
            "certificate expiry notifications sent",
            tenants_notified=result.tenants_notified,
            alerts_sent=result.alerts_sent,
        )
        return {
            "tenantsNotified": result.tenants_notified,
            "alertsSent": result.alerts_sent,
        }
    except AppError:
        _log.warning("certificate expiry notifier application error", exc_info=True)
        raise
    except Exception as exc:
        _log.error("certificate expiry notifier unexpected error", exc_info=True)
        raise InternalError() from exc
