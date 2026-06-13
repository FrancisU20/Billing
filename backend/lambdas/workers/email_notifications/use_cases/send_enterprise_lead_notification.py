from __future__ import annotations

"""Use case: notify the sales team about a new Enterprise lead capture."""

from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class SendEnterpriseLeadNotificationUseCase:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender

    def execute(
        self, *, superadmin_email: str, trade_name: str, ruc: str, email: str, plan_id: str
    ) -> None:
        if not superadmin_email or not ruc:
            raise ValidationError(
                "superadmin_email and ruc are required to send the enterprise lead notification"
            )

        try:
            self._email_sender.send_enterprise_lead_notification(
                superadmin_email=superadmin_email,
                trade_name=trade_name,
                ruc=ruc,
                email=email,
                plan_id=plan_id,
            )
            _log.info("enterprise lead notification sent", ruc=ruc)
        except Exception as exc:
            _log.error("error sending enterprise lead notification", error=str(exc), exc_info=True)
            raise InternalError()
