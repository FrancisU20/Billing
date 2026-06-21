from __future__ import annotations

"""
SignDocumentUseCase — flujo SIGN del worker `invoice_processor`.

Idempotente ante entregas duplicadas de SQS: si el documento ya no está PENDING,
es un mensaje SIGN repetido (procesado por una invocación anterior) y se ignora.
"""

from lambdas.documents.domain.entities import DocumentStatus
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository
from lambdas.invoice_processor import sri_error_classifier, xml_builder
from lambdas.invoice_processor.infra.certificate_loader import load_certificate
from lambdas.invoice_processor.ports import IQueuePublisher, ISriClient
from lambdas.invoice_processor.signing import sign_xades_bes
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from shared.errors import ExternalServiceError
from shared.logger import get_logger

_log = get_logger(__name__)

_FIRST_POLL_DELAY_SECONDS = 30


class SignDocumentUseCase:
    def __init__(
        self,
        documents_repo: IDocumentsRepository,
        tenant_repo: DynamoTenantRepository,
        sri_client: ISriClient,
        queue_publisher: IQueuePublisher,
    ) -> None:
        self._documents_repo = documents_repo
        self._tenant_repo = tenant_repo
        self._sri_client = sri_client
        self._queue_publisher = queue_publisher

    def execute(self, *, tenant_id: str, document_id: str) -> None:
        document = self._documents_repo.get(tenant_id, document_id)
        if document.status != DocumentStatus.PENDING:
            _log.info(
                "SIGN message ignored — document is not PENDING (duplicate delivery)",
                document_id=document_id,
                status=document.status.value,
            )
            return

        tenant = self._tenant_repo.get_by_id(tenant_id)
        private_key, certificate = load_certificate(tenant.certificate_secret_arn)

        xml = xml_builder.build_invoice_xml(document, tenant)
        signed_xml = sign_xades_bes(xml, private_key, certificate)

        result = self._sri_client.recepcion(environment=document.sri_environment, xmls=[signed_xml])

        if result.received:
            self._documents_repo.update_status(
                tenant_id,
                document_id,
                expected_status=DocumentStatus.PENDING,
                new_status=DocumentStatus.PROCESSING,
            )
            self._queue_publisher.enqueue_poll(
                tenant_id=tenant_id,
                document_id=document_id,
                access_key=document.access_key,
                attempt=1,
                delay_seconds=_FIRST_POLL_DELAY_SECONDS,
            )
            return

        first_error = result.errors[0] if result.errors else None
        classification = sri_error_classifier.classify(first_error.code if first_error else "")
        sri_errors = [e.to_dict() for e in result.errors]

        if classification == sri_error_classifier.PERMANENT:
            self._documents_repo.update_status(
                tenant_id,
                document_id,
                expected_status=DocumentStatus.PENDING,
                new_status=DocumentStatus.REJECTED,
                sri_errors=sri_errors,
            )
            _log.warning("document permanently rejected by SRI (DEVUELTA)", document_id=document_id)
            return

        self._documents_repo.update_status(
            tenant_id,
            document_id,
            expected_status=DocumentStatus.PENDING,
            new_status=DocumentStatus.FAILED,
            increment_retry=True,
        )
        raise ExternalServiceError("SRI devolvió un error reintentable en recepción")
