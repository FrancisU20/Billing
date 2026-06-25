from __future__ import annotations

import unittest
from unittest.mock import patch

from lambdas.documents.domain.entities import DocumentStatus
from lambdas.invoice_processor.ports import RecepcionResult, SriErrorDetail
from lambdas.invoice_processor.use_cases.sign_document import SignDocumentUseCase
from shared.errors import ExternalServiceError
from tests.unit.lambdas.invoice_processor.fixtures import make_document, make_invoice_tenant
from tests.unit.support import FakeTenantRepository

# ── Fakes ─────────────────────────────────────────────────────────────────────


class FakeDocumentsRepository:
    def __init__(self, document) -> None:
        self.document = document
        self.update_calls: list[dict] = []
        self.extra_documents: dict[str, object] = {}

    def get(self, tenant_id, document_id):
        if document_id in self.extra_documents:
            return self.extra_documents[document_id]
        return self.document

    def update_status(self, tenant_id, document_id, **kwargs):
        self.update_calls.append(kwargs)
        self.document.status = kwargs["new_status"]
        return True


class FakeSriClient:
    def __init__(self, result: RecepcionResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    def recepcion(self, *, environment, xmls):
        self.calls.append({"environment": environment, "xmls": xmls})
        return self.result

    def autorizacion(self, *, environment, access_key):
        raise NotImplementedError


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


class SignDocumentUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tenant = make_invoice_tenant()
        self.document = make_document(tenant_id=self.tenant.id, status=DocumentStatus.PENDING)
        self.cert_patch = patch(
            "lambdas.invoice_processor.use_cases.sign_document.load_certificate",
            return_value=(object(), object()),
        )
        self.cert_patch.start()
        self.sign_patch = patch(
            "lambdas.invoice_processor.use_cases.sign_document.sign_xades_bes",
            return_value="<signed/>",
        )
        self.sign_patch.start()

    def tearDown(self) -> None:
        self.cert_patch.stop()
        self.sign_patch.stop()

    def _execute(self, sri_client):
        repo = FakeDocumentsRepository(self.document)
        tenant_repo = _tenant_repo_with(self.tenant)
        publisher = FakeQueuePublisher()
        use_case = SignDocumentUseCase(repo, tenant_repo, sri_client, publisher)
        use_case.execute(tenant_id=self.tenant.id, document_id=self.document.document_id)
        return repo, publisher

    def test_recibida_marks_processing_and_enqueues_first_poll(self) -> None:
        sri_client = FakeSriClient(RecepcionResult(received=True, errors=[]))
        repo, publisher = self._execute(sri_client)

        self.assertEqual(repo.update_calls[0]["new_status"], DocumentStatus.PROCESSING)
        self.assertEqual(len(publisher.polls_enqueued), 1)
        self.assertEqual(publisher.polls_enqueued[0]["attempt"], 1)

    def test_devuelta_with_permanent_error_marks_rejected_without_raising(self) -> None:
        sri_client = FakeSriClient(
            RecepcionResult(
                received=False, errors=[SriErrorDetail(code="43", message="FIRMA INVALIDA")]
            )
        )
        repo, publisher = self._execute(sri_client)

        self.assertEqual(repo.update_calls[0]["new_status"], DocumentStatus.REJECTED)
        self.assertEqual(repo.update_calls[0]["sri_errors"][0]["category"], "FIRMA")
        self.assertEqual(publisher.polls_enqueued, [])

    def test_devuelta_with_retryable_error_marks_failed_and_raises(self) -> None:
        sri_client = FakeSriClient(
            RecepcionResult(
                received=False, errors=[SriErrorDetail(code="70", message="no disponible")]
            )
        )
        repo = FakeDocumentsRepository(self.document)
        tenant_repo = _tenant_repo_with(self.tenant)
        publisher = FakeQueuePublisher()
        use_case = SignDocumentUseCase(repo, tenant_repo, sri_client, publisher)

        with self.assertRaises(ExternalServiceError):
            use_case.execute(tenant_id=self.tenant.id, document_id=self.document.document_id)

        self.assertEqual(repo.update_calls[0]["new_status"], DocumentStatus.FAILED)
        self.assertTrue(repo.update_calls[0]["increment_retry"])

    def test_ignores_message_when_document_is_not_pending(self) -> None:
        self.document.status = DocumentStatus.PROCESSING
        sri_client = FakeSriClient(RecepcionResult(received=True, errors=[]))
        repo, publisher = self._execute(sri_client)

        self.assertEqual(repo.update_calls, [])
        self.assertEqual(sri_client.calls, [])
        self.assertEqual(publisher.polls_enqueued, [])

    def test_credit_note_builds_xml_with_parent_lookup(self) -> None:
        parent = make_document(document_id="parent-1", tenant_id=self.tenant.id)
        self.document = make_document(
            document_id="doc-2",
            tenant_id=self.tenant.id,
            status=DocumentStatus.PENDING,
            doc_type="04",
            related_document_id="parent-1",
            credit_note_reason="Devolución de mercadería",
        )
        repo = FakeDocumentsRepository(self.document)
        repo.extra_documents["parent-1"] = parent
        tenant_repo = _tenant_repo_with(self.tenant)
        publisher = FakeQueuePublisher()
        sri_client = FakeSriClient(RecepcionResult(received=True, errors=[]))

        with (
            patch(
                "lambdas.invoice_processor.use_cases.sign_document.xml_builder.build_credit_note_xml",
                return_value="<notaCredito/>",
            ) as build_cn,
            patch(
                "lambdas.invoice_processor.use_cases.sign_document.xml_builder.build_invoice_xml"
            ) as build_invoice,
        ):
            use_case = SignDocumentUseCase(repo, tenant_repo, sri_client, publisher)
            use_case.execute(tenant_id=self.tenant.id, document_id=self.document.document_id)

        build_cn.assert_called_once_with(self.document, self.tenant, parent)
        build_invoice.assert_not_called()


if __name__ == "__main__":
    unittest.main()
