from __future__ import annotations

"""Use case: notify the tenant that SRI authorization could not be confirmed after retries."""

from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class SendDocumentFailedPermanentUseCase:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender

    def execute(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
        doc_type: str = "01",
    ) -> None:
        if not email:
            raise ValidationError("email is required to send the document failed notice")

        try:
            self._email_sender.send_document_failed_permanent(
                email=email,
                legal_rep_name=legal_rep_name,
                document_id=document_id,
                doc_type=doc_type,
                access_key=access_key,
            )
            _log.info("document failed permanent email sent", email=email, document_id=document_id)
        except Exception as exc:
            _log.error(
                "error sending document failed permanent email", error=str(exc), exc_info=True
            )
            raise InternalError() from exc
