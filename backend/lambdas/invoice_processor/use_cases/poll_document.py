from __future__ import annotations

"""
PollDocumentUseCase — flujo POLL del worker `invoice_processor`.

Idempotente ante entregas duplicadas de SQS: si el documento ya no está
PROCESSING, un POLL anterior ya lo resolvió (AUTHORIZED/REJECTED/FAILED_PERMANENT)
y este mensaje se ignora.
"""

from datetime import UTC, datetime

from lambdas.documents.domain.entities import DocumentStatus
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository
from lambdas.invoice_processor import ride_builder
from lambdas.invoice_processor.events import (
    DocumentAuthorizedEvent,
    DocumentBuyerNotificationRequestedEvent,
    DocumentFailedPermanentEvent,
    DocumentRejectedEvent,
)
from lambdas.invoice_processor.ports import IDocumentStorage, IQueuePublisher, ISriClient
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from shared.logger import get_logger

_log = get_logger(__name__)

_MAX_POLL_ATTEMPTS = 5
_BASE_BACKOFF_SECONDS = 30
_MAX_BACKOFF_SECONDS = 600


def _next_delay_seconds(attempt: int) -> int:
    return min(_BASE_BACKOFF_SECONDS * 2**attempt, _MAX_BACKOFF_SECONDS)


def _parse_authorized_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)

    raw = value.strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        _log.warning("SRI authorized_at could not be parsed; using worker timestamp", value=value)
        return datetime.now(UTC)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class PollDocumentUseCase:
    def __init__(
        self,
        documents_repo: IDocumentsRepository,
        tenant_repo: DynamoTenantRepository,
        sri_client: ISriClient,
        storage: IDocumentStorage,
        queue_publisher: IQueuePublisher,
    ) -> None:
        self._documents_repo = documents_repo
        self._tenant_repo = tenant_repo
        self._sri_client = sri_client
        self._storage = storage
        self._queue_publisher = queue_publisher

    def execute(self, *, tenant_id: str, document_id: str, access_key: str, attempt: int) -> None:
        document = self._documents_repo.get(tenant_id, document_id)
        if document.status != DocumentStatus.PROCESSING:
            _log.info(
                "POLL message ignored — document is not PROCESSING (duplicate delivery)",
                document_id=document_id,
                status=document.status.value,
            )
            return

        tenant = self._tenant_repo.get_by_id(tenant_id)
        result = self._sri_client.autorizacion(
            environment=document.sri_environment, access_key=access_key
        )

        if result.status == "AUTORIZADO":
            authorized_at = _parse_authorized_at(result.authorized_at)
            document.authorization_number = result.authorization_number
            document.authorized_at = authorized_at
            ride_pdf = ride_builder.build_ride_pdf(document, tenant)
            xml_s3_key, ride_s3_key = self._storage.put_authorized_document(
                tenant_id=tenant_id,
                document_id=document_id,
                year=document.issued_at.year,
                # El XML viene del eco de la respuesta de autorización del SRI (fuente de
                # verdad legal), no se re-genera ni se persiste el firmado en SIGN.
                signed_xml=result.signed_xml or "",
                ride_pdf=ride_pdf,
            )
            self._documents_repo.update_status(
                tenant_id,
                document_id,
                expected_status=DocumentStatus.PROCESSING,
                new_status=DocumentStatus.AUTHORIZED,
                authorization_number=result.authorization_number,
                authorized_at=authorized_at,
                xml_s3_key=xml_s3_key,
                ride_s3_key=ride_s3_key,
            )
            issuer_name = tenant.legal_name or tenant.trade_name
            self._queue_publisher.publish_event(
                DocumentAuthorizedEvent(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    access_key=access_key,
                    authorization_number=result.authorization_number or "",
                    tenant_email=tenant.email,
                    legal_rep_name=tenant.legal_rep_name,
                    issuer_name=issuer_name,
                    issuer_ruc=tenant.ruc,
                    buyer_name=document.buyer_name,
                    buyer_id=document.buyer_id,
                    buyer_email=document.buyer_email or "",
                    sequential_display=document.sequential_display,
                    issued_at=document.issued_at.isoformat(),
                    authorized_at=authorized_at.isoformat(),
                    total=str(document.total),
                    currency="USD",
                )
            )
            self._queue_publisher.publish_event(
                DocumentBuyerNotificationRequestedEvent(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    issuer_name=issuer_name,
                    issuer_ruc=tenant.ruc,
                )
            )
            return

        if result.status == "EN_PROCESO":
            if attempt < _MAX_POLL_ATTEMPTS:
                self._queue_publisher.enqueue_poll(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    access_key=access_key,
                    attempt=attempt + 1,
                    delay_seconds=_next_delay_seconds(attempt),
                )
                return

            self._documents_repo.update_status(
                tenant_id,
                document_id,
                expected_status=DocumentStatus.PROCESSING,
                new_status=DocumentStatus.FAILED_PERMANENT,
            )
            self._queue_publisher.publish_event(
                DocumentFailedPermanentEvent(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    access_key=access_key,
                    tenant_email=tenant.email,
                    legal_rep_name=tenant.legal_rep_name,
                )
            )
            return

        sri_errors = [{"code": e.code, "message": e.message} for e in (result.errors or [])]
        self._documents_repo.update_status(
            tenant_id,
            document_id,
            expected_status=DocumentStatus.PROCESSING,
            new_status=DocumentStatus.REJECTED,
            rejected_at=datetime.now(UTC),
            sri_errors=sri_errors,
        )
        self._queue_publisher.publish_event(
            DocumentRejectedEvent(
                tenant_id=tenant_id,
                document_id=document_id,
                access_key=access_key,
                tenant_email=tenant.email,
                legal_rep_name=tenant.legal_rep_name,
                sri_errors=sri_errors,
            )
        )
