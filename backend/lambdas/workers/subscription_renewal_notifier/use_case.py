from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)

_NOTIFIER_USER_ID = "system:subscription-renewal-notifier"
_REMINDER_DAYS = 7
_SECONDS_PER_DAY = 86400


@dataclass(frozen=True)
class NotifySubscriptionRenewalResult:
    reminders_sent: int
    expirations_processed: int


class NotifySubscriptionRenewalUseCase:
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

    def execute(self) -> NotifySubscriptionRenewalResult:
        # Fetch active tenants whose cycle ends within REMINDER_DAYS from now
        # (also includes already-expired ones since they are before now)
        before = self._now + timedelta(days=_REMINDER_DAYS)
        candidates = self._tenant_repo.list_with_subscription_expiry_due(before)

        reminders_sent = 0
        expirations_processed = 0

        for tenant in candidates:
            try:
                changed = self._process_tenant(tenant)
                if changed:
                    self._tenant_repo.save(tenant, user_id=_NOTIFIER_USER_ID)
            except OptimisticLockError:
                _log.warning(
                    "subscription renewal notifier lost concurrent update; will retry on next run",
                    tenant_id=tenant.id,
                )
                continue
            except Exception:
                _log.error(
                    "unexpected error processing tenant for subscription renewal",
                    tenant_id=tenant.id,
                    exc_info=True,
                )
                continue

            if changed == "expired":
                expirations_processed += 1
            elif changed == "reminder":
                reminders_sent += 1

        return NotifySubscriptionRenewalResult(
            reminders_sent=reminders_sent,
            expirations_processed=expirations_processed,
        )

    def _process_tenant(self, tenant) -> str | None:
        ends_at = tenant.plan_cycle_ends_at
        if ends_at is None:
            return None

        if ends_at <= self._now:
            # Subscription has already expired
            tenant.expire_subscription(updated_by=_NOTIFIER_USER_ID)
            self._email_sender.send_subscription_expired(
                email=tenant.email,
                legal_rep_name=tenant.legal_rep_name,
                trade_name=tenant.trade_name,
            )
            return "expired"

        # Still active — send reminder if not already sent
        if tenant.subscription_renewal_reminder_sent_at is None:
            days_remaining = max(
                1,
                math.ceil((ends_at - self._now).total_seconds() / _SECONDS_PER_DAY),
            )
            self._email_sender.send_subscription_renewal_reminder(
                email=tenant.email,
                legal_rep_name=tenant.legal_rep_name,
                trade_name=tenant.trade_name,
                plan_cycle_ends_at=ends_at.isoformat(),
                days_remaining=days_remaining,
            )
            tenant.mark_renewal_reminder_sent(
                sent_at=self._now,
                updated_by=_NOTIFIER_USER_ID,
            )
            return "reminder"

        return None
