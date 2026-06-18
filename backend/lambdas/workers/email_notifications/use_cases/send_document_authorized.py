from __future__ import annotations

"""Use case: notify the tenant that a document was authorized by the SRI."""

from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class SendDocumentAuthorizedUseCase:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender

    def execute(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
        authorization_number: str,
    ) -> None:
        if not email:
            raise ValidationError("email is required to send the document authorized notice")

        try:
            self._email_sender.send_document_authorized(
                email=email,
                legal_rep_name=legal_rep_name,
                document_id=document_id,
                access_key=access_key,
                authorization_number=authorization_number,
            )
            _log.info("document authorized email sent", email=email, document_id=document_id)
        except Exception as exc:
            _log.error("error sending document authorized email", error=str(exc), exc_info=True)
            raise InternalError() from exc
