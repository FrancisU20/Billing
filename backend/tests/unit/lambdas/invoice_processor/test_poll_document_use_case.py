from __future__ import annotations

import unittest

from lambdas.documents.domain.entities import DocumentStatus
from lambdas.invoice_processor.events import (
    DocumentAuthorizedEvent,
    DocumentFailedPermanentEvent,
    DocumentRejectedEvent,
)
from lambdas.invoice_processor.ports import AutorizacionResult, SriErrorDetail
from lambdas.invoice_processor.use_cases.poll_document import PollDocumentUseCase
from tests.unit.lambdas.invoice_processor.fixtures import (
    ACCESS_KEY,
    make_document,
    make_invoice_tenant,
)
from tests.unit.support import FakeTenantRepository

# ── Fakes ─────────────────────────────────────────────────────────────────────


class FakeDocumentsRepository:
    def __init__(self, document) -> None:
        self.document = document
        self.update_calls: list[dict] = []

    def get(self, tenant_id, document_id):
        return self.document

    def update_status(self, tenant_id, document_id, **kwargs):
        self.update_calls.append(kwargs)
        self.document.status = kwargs["new_status"]
        return True


class FakeSriClient:
    def __init__(self, result: AutorizacionResult) -> None:
        self.result = result

    def recepcion(self, *, environment, xmls):
        raise NotImplementedError

    def autorizacion(self, *, environment, access_key):
        return self.result


class FakeStorage:
    def __init__(self) -> None:
        self.stored: list[dict] = []

    def put_authorized_document(self, **kwargs):
        self.stored.append(kwargs)
        return ("xml-key", "ride-key")


class FakeQueuePublisher:
    def __init__(self) -> None:
        self.polls_enqueued: list[dict] = []
        self.events_published: list = []

    def enqueue_poll(self, **kwargs):
        self.polls_enqueued.append(kwargs)

    def publish_event(self, event):
        self.events_published.append(event)


def _tenant_repo_with(tenant):
    repo = FakeTenantRepository()
    repo.tenants[tenant.id] = tenant
    return repo


# ── Tests ─────────────────────────────────────────────────────────────────────


class PollDocumentUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tenant = make_invoice_tenant()
        self.document = make_document(tenant_id=self.tenant.id, status=DocumentStatus.PROCESSING)

    def _build(self, result: AutorizacionResult):
        repo = FakeDocumentsRepository(self.document)
        tenant_repo = _tenant_repo_with(self.tenant)
        sri_client = FakeSriClient(result)
        storage = FakeStorage()
        publisher = FakeQueuePublisher()
        use_case = PollDocumentUseCase(repo, tenant_repo, sri_client, storage, publisher)
        return use_case, repo, storage, publisher

    def test_autorizado_stores_documents_and_marks_authorized(self) -> None:
        result = AutorizacionResult(
            status="AUTORIZADO",
            authorization_number="123",
            authorized_at="2026-06-17T10:00:00Z",
            signed_xml="<factura/>",
        )
        use_case, repo, storage, publisher = self._build(result)

        use_case.execute(
            tenant_id=self.tenant.id,
            document_id=self.document.document_id,
            access_key=ACCESS_KEY,
            attempt=1,
        )

        self.assertEqual(repo.update_calls[0]["new_status"], DocumentStatus.AUTHORIZED)
        self.assertEqual(len(storage.stored), 1)
        self.assertEqual(len(publisher.events_published), 1)
        self.assertIsInstance(publisher.events_published[0], DocumentAuthorizedEvent)

    def test_en_proceso_reenqueues_with_backoff(self) -> None:
        use_case, repo, storage, publisher = self._build(AutorizacionResult(status="EN_PROCESO"))

        use_case.execute(
            tenant_id=self.tenant.id,
            document_id=self.document.document_id,
            access_key=ACCESS_KEY,
            attempt=2,
        )

        self.assertEqual(repo.update_calls, [])
        self.assertEqual(len(publisher.polls_enqueued), 1)
        self.assertEqual(publisher.polls_enqueued[0]["attempt"], 3)
        self.assertEqual(publisher.polls_enqueued[0]["delay_seconds"], 120)  # 30*2**2

    def test_en_proceso_exhausted_marks_failed_permanent(self) -> None:
        use_case, repo, storage, publisher = self._build(AutorizacionResult(status="EN_PROCESO"))

        use_case.execute(
            tenant_id=self.tenant.id,
            document_id=self.document.document_id,
            access_key=ACCESS_KEY,
            attempt=5,
        )

        self.assertEqual(repo.update_calls[0]["new_status"], DocumentStatus.FAILED_PERMANENT)
        self.assertEqual(publisher.polls_enqueued, [])
        self.assertIsInstance(publisher.events_published[0], DocumentFailedPermanentEvent)

    def test_rechazado_marks_rejected_and_publishes_event(self) -> None:
        result = AutorizacionResult(
            status="RECHAZADO", errors=[SriErrorDetail(code="44", message="RUC no autorizado")]
        )
        use_case, repo, storage, publisher = self._build(result)

        use_case.execute(
            tenant_id=self.tenant.id,
            document_id=self.document.document_id,
            access_key=ACCESS_KEY,
            attempt=1,
        )

        self.assertEqual(repo.update_calls[0]["new_status"], DocumentStatus.REJECTED)
        self.assertIsInstance(publisher.events_published[0], DocumentRejectedEvent)

    def test_ignores_message_when_document_is_not_processing(self) -> None:
        self.document.status = DocumentStatus.AUTHORIZED
        use_case, repo, storage, publisher = self._build(AutorizacionResult(status="AUTORIZADO"))

        use_case.execute(
            tenant_id=self.tenant.id,
            document_id=self.document.document_id,
            access_key=ACCESS_KEY,
            attempt=1,
        )

        self.assertEqual(repo.update_calls, [])
        self.assertEqual(storage.stored, [])
        self.assertEqual(publisher.events_published, [])


if __name__ == "__main__":
    unittest.main()
