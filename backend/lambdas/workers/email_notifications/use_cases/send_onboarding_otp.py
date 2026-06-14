from __future__ import annotations

"""Use case: send the onboarding OTP email."""

from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class SendOnboardingOtpUseCase:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender

    def execute(
        self,
        *,
        email: str,
        legal_rep_name: str,
        otp: str,
        expires_at: str,
    ) -> None:
        if not email or not otp:
            raise ValidationError("email and otp are required to send onboarding verification")

        try:
            self._email_sender.send_onboarding_otp(
                email=email,
                legal_rep_name=legal_rep_name,
                otp=otp,
                expires_at=expires_at,
            )
            _log.info("onboarding otp email sent", email=email)
        except Exception as exc:
            _log.error("error sending onboarding otp email", error=str(exc), exc_info=True)
            raise InternalError() from exc
