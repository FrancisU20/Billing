from __future__ import annotations

"""
Lambda `invoice_processor` — firma XAdES-BES, envío SRI, polling de autorización.

Desplegado como dos funciones CDK (`invoice-processor-sign` / `invoice-processor-poll`)
con el mismo código y distinto `reserved_concurrent_executions`, cada una suscrita a
su cola (`invoice-sign` / `invoice-poll`). El routing por `type` es el mismo en
ambas — ver `context/INVOICES.md`.
"""

from lambdas._base.sqs_handler import SQSRecord, sqs_handler
from lambdas.documents.infra.documents_repository import DynamoDocumentsRepository
from lambdas.invoice_processor.infra.s3_document_storage import S3DocumentStorage
from lambdas.invoice_processor.infra.sqs_event_publisher import SQSQueuePublisher
from lambdas.invoice_processor.sri_client import SriSoapClient
from lambdas.invoice_processor.use_cases.poll_document import PollDocumentUseCase
from lambdas.invoice_processor.use_cases.sign_document import SignDocumentUseCase
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from shared.config import env
from shared.db.client import get_table
from shared.logger import get_logger

_log = get_logger(__name__)

# ── Cold start ────────────────────────────────────────────────────────────────
_documents_repo = DynamoDocumentsRepository(get_table("DOCUMENTS_TABLE"))
_tenant_repo = DynamoTenantRepository(get_table("TENANTS_TABLE"), None, None)
_sri_client = SriSoapClient()
_queue_publisher = SQSQueuePublisher(
    poll_queue_url=env("POLL_QUEUE_URL", ""),
    email_notifications_queue_url=env("EMAIL_NOTIFICATIONS_QUEUE_URL", ""),
)
_storage = S3DocumentStorage(bucket_name=env("DOCUMENTS_BUCKET", ""))

_sign_use_case = SignDocumentUseCase(_documents_repo, _tenant_repo, _sri_client, _queue_publisher)
_poll_use_case = PollDocumentUseCase(
    _documents_repo, _tenant_repo, _sri_client, _storage, _queue_publisher
)


@sqs_handler
def handler(record: SQSRecord, context) -> None:
    message_type = record.body.get("type")

    if message_type == "SIGN":
        _sign_use_case.execute(
            tenant_id=record.body["tenant_id"],
            document_id=record.body["document_id"],
        )
        return

    if message_type == "POLL":
        _poll_use_case.execute(
            tenant_id=record.body["tenant_id"],
            document_id=record.body["document_id"],
            access_key=record.body["access_key"],
            attempt=record.body.get("attempt", 1),
        )
        return

    _log.warning("unknown message type ignored", message_type=message_type)
