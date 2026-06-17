from __future__ import annotations

"""Use case: send a subscription renewal reminder to the tenant owner."""

from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class SendSubscriptionRenewalReminderUseCase:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender

    def execute(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        plan_cycle_ends_at: str,
        days_remaining: int,
        renewal_url: str,
    ) -> None:
        if not email:
            raise ValidationError("email is required to send the renewal reminder")

        try:
            self._email_sender.send_subscription_renewal_reminder(
                email=email,
                legal_rep_name=legal_rep_name,
                trade_name=trade_name,
                plan_cycle_ends_at=plan_cycle_ends_at,
                days_remaining=days_remaining,
                renewal_url=renewal_url,
            )
            _log.info(
                "subscription renewal reminder sent",
                email=email,
                days_remaining=days_remaining,
            )
        except Exception as exc:
            _log.error("error sending renewal reminder", error=str(exc), exc_info=True)
            raise InternalError() from exc
