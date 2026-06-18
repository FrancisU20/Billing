from __future__ import annotations

"""Use case: send authorized XML + RIDE to the invoice buyer."""

from datetime import UTC, datetime

from lambdas.documents.domain.entities import BuyerNotificationStatus, DocumentStatus
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository
from lambdas.workers.email_notifications.ports import DocumentAttachmentReader, EmailSender
from shared.errors import InternalError
from shared.logger import get_logger

_log = get_logger(__name__)


class SendDocumentToBuyerUseCase:
    def __init__(
        self,
        documents_repo: IDocumentsRepository,
        attachment_reader: DocumentAttachmentReader,
        email_sender: EmailSender,
    ) -> None:
        self._documents_repo = documents_repo
        self._attachment_reader = attachment_reader
        self._email_sender = email_sender

    def execute(self, *, tenant_id: str, document_id: str) -> None:
        document = self._documents_repo.get(tenant_id, document_id)
        if document.status != DocumentStatus.AUTHORIZED:
            _log.warning(
                "buyer notification skipped: document is not authorized",
                tenant_id=tenant_id,
                document_id=document_id,
                status=document.status.value,
            )
            return

        if not self._documents_repo.begin_buyer_notification(tenant_id, document_id):
            return

        if not document.buyer_email:
            self._documents_repo.mark_buyer_notification_status(
                tenant_id,
                document_id,
                status=BuyerNotificationStatus.SKIPPED_NO_EMAIL,
            )
            _log.info(
                "buyer notification skipped: buyer email missing",
                tenant_id=tenant_id,
                document_id=document_id,
            )
            return

        if not document.xml_s3_key or not document.ride_s3_key:
            self._mark_failed_and_raise(
                tenant_id,
                document_id,
                "authorized document does not have XML/RIDE S3 keys",
            )

        try:
            attachments = self._attachment_reader.get_authorized_document(
                xml_s3_key=document.xml_s3_key,
                ride_s3_key=document.ride_s3_key,
                document_id=document_id,
            )
            self._email_sender.send_document_to_buyer(
                email=document.buyer_email,
                buyer_name=document.buyer_name,
                document_id=document_id,
                access_key=document.access_key,
                authorization_number=document.authorization_number or "",
                xml_content=attachments.xml_content,
                xml_filename=attachments.xml_filename,
                ride_content=attachments.ride_content,
                ride_filename=attachments.ride_filename,
            )
            self._documents_repo.mark_buyer_notification_status(
                tenant_id,
                document_id,
                status=BuyerNotificationStatus.SENT,
                notified_at=datetime.now(UTC),
            )
            _log.info(
                "buyer document email sent",
                tenant_id=tenant_id,
                document_id=document_id,
                buyer_email=document.buyer_email,
            )
        except Exception as exc:
            self._documents_repo.mark_buyer_notification_status(
                tenant_id,
                document_id,
                status=BuyerNotificationStatus.FAILED,
                error=str(exc),
            )
            _log.error("error sending buyer document email", error=str(exc), exc_info=True)
            raise InternalError() from exc

    def _mark_failed_and_raise(self, tenant_id: str, document_id: str, error: str) -> None:
        self._documents_repo.mark_buyer_notification_status(
            tenant_id,
            document_id,
            status=BuyerNotificationStatus.FAILED,
            error=error,
        )
        raise InternalError(error)
