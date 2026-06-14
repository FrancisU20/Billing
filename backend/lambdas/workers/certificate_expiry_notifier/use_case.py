from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.workers.email_notifications.ports import EmailSender
from shared.certificates.expiry import CERTIFICATE_EXPIRY_ALERT_THRESHOLDS_DAYS, SECONDS_PER_DAY
from shared.errors import OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)

_NOTIFIER_USER_ID = "system:certificate-expiry-notifier"


@dataclass(frozen=True)
class NotifyCertificateExpiryResult:
    tenants_notified: int
    alerts_sent: int


class NotifyCertificateExpiryUseCase:
    def __init__(
        self,
        tenant_repo: ITenantRepository,
        email_sender: EmailSender,
        *,
        now: datetime,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._email_sender = email_sender
        self._now = now

    def execute(self) -> NotifyCertificateExpiryResult:
        before = self._now + timedelta(days=max(CERTIFICATE_EXPIRY_ALERT_THRESHOLDS_DAYS))
        candidates = self._tenant_repo.list_with_certificate_expiry_due(before)

        tenants_notified = 0
        alerts_sent = 0

        for tenant in candidates:
            thresholds = tenant.due_certificate_expiry_alerts(self._now)
            if not thresholds:
                continue

            for threshold in thresholds:
                days_remaining = max(
                    0,
                    math.ceil(
                        (tenant.cert_expires_at - self._now).total_seconds() / SECONDS_PER_DAY
                    ),
                )
                self._email_sender.send_certificate_expiry_alert(
                    email=tenant.email,
                    legal_rep_name=tenant.legal_rep_name,
                    trade_name=tenant.trade_name,
                    ruc=tenant.ruc,
                    cert_expires_at=tenant.cert_expires_at.isoformat(),
                    days_remaining=days_remaining,
                )
                tenant.mark_certificate_expiry_alert_sent(
                    threshold, self._now, updated_by=_NOTIFIER_USER_ID
                )
                alerts_sent += 1

            try:
                self._tenant_repo.save(tenant, user_id=_NOTIFIER_USER_ID)
                tenants_notified += 1
            except OptimisticLockError:
                _log.warning(
                    "certificate expiry alert sent but tenant save lost a "
                    "concurrent update; will retry on next run",
                    tenant_id=tenant.id,
                )

        return NotifyCertificateExpiryResult(
            tenants_notified=tenants_notified, alerts_sent=alerts_sent
        )
