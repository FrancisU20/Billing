from __future__ import annotations

"""Use case: notify the tenant owner that their subscription has expired."""

from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class SendSubscriptionExpiredUseCase:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender

    def execute(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        renewal_url: str,
    ) -> None:
        if not email:
            raise ValidationError("email is required to send the subscription expired notice")

        try:
            self._email_sender.send_subscription_expired(
                email=email,
                legal_rep_name=legal_rep_name,
                trade_name=trade_name,
                renewal_url=renewal_url,
            )
            _log.info("subscription expired email sent", email=email)
        except Exception as exc:
            _log.error("error sending subscription expired email", error=str(exc), exc_info=True)
            raise InternalError() from exc
