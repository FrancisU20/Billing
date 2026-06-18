from __future__ import annotations

import unittest

from lambdas.documents.domain.entities import BuyerNotificationStatus, DocumentStatus
from lambdas.workers.email_notifications.ports import DocumentAttachments
from lambdas.workers.email_notifications.use_cases.send_document_to_buyer import (
    SendDocumentToBuyerUseCase,
)
from shared.errors import InternalError
from tests.unit.lambdas.invoice_processor.fixtures import make_document


class FakeDocumentsRepository:
    def __init__(self, document, *, begin_result: bool = True) -> None:
        self.document = document
        self.begin_result = begin_result
        self.begin_calls: list[tuple[str, str]] = []
        self.status_calls: list[dict] = []

    def get(self, tenant_id: str, document_id: str):
        return self.document

    def begin_buyer_notification(self, tenant_id: str, document_id: str) -> bool:
        self.begin_calls.append((tenant_id, document_id))
        return self.begin_result

    def mark_buyer_notification_status(self, tenant_id: str, document_id: str, **kwargs):
        self.status_calls.append(kwargs)
        self.document.buyer_notification_status = kwargs["status"]
        return True


class FakeAttachmentReader:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.calls: list[dict] = []
        self.should_fail = should_fail

    def get_authorized_document(self, **kwargs) -> DocumentAttachments:
        self.calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("S3 unavailable")
        return DocumentAttachments(
            xml_content=b"<factura/>",
            xml_filename="doc-1.xml",
            ride_content=b"%PDF",
            ride_filename="doc-1.pdf",
        )


class FakeEmailSender:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.calls: list[dict] = []
        self.should_fail = should_fail

    def send_document_to_buyer(self, **kwargs) -> None:
        if self.should_fail:
            raise RuntimeError("Brevo unavailable")
        self.calls.append(kwargs)


def _authorized_document(**overrides):
    defaults = dict(
        status=DocumentStatus.AUTHORIZED,
        buyer_email="buyer@example.com",
        buyer_name="Cliente Demo",
        authorization_number="123",
        xml_s3_key="tenants/t1/docs/2026/doc-1.xml",
        ride_s3_key="tenants/t1/docs/2026/doc-1.pdf",
    )
    defaults.update(overrides)
    return make_document(**defaults)


class SendDocumentToBuyerUseCaseTests(unittest.TestCase):
    def test_sends_xml_and_ride_to_buyer_and_marks_sent(self) -> None:
        repo = FakeDocumentsRepository(_authorized_document())
        reader = FakeAttachmentReader()
        sender = FakeEmailSender()

        SendDocumentToBuyerUseCase(repo, reader, sender).execute(
            tenant_id="tenant-1",
            document_id="doc-1",
            issuer_name="Empresa Demo S.A.",
            issuer_ruc="1792146739001",
        )

        self.assertEqual(len(repo.begin_calls), 1)
        self.assertEqual(len(reader.calls), 1)
        self.assertEqual(len(sender.calls), 1)
        self.assertEqual(sender.calls[0]["email"], "buyer@example.com")
        self.assertEqual(sender.calls[0]["issuer_name"], "Empresa Demo S.A.")
        self.assertEqual(sender.calls[0]["issuer_ruc"], "1792146739001")
        self.assertEqual(sender.calls[0]["xml_content"], b"<factura/>")
        self.assertEqual(sender.calls[0]["ride_content"], b"%PDF")
        self.assertEqual(repo.status_calls[-1]["status"], BuyerNotificationStatus.SENT)
        self.assertIsNotNone(repo.status_calls[-1]["notified_at"])

    def test_skips_when_buyer_email_is_missing(self) -> None:
        repo = FakeDocumentsRepository(_authorized_document(buyer_email=None))
        reader = FakeAttachmentReader()
        sender = FakeEmailSender()

        SendDocumentToBuyerUseCase(repo, reader, sender).execute(
            tenant_id="tenant-1", document_id="doc-1"
        )

        self.assertEqual(reader.calls, [])
        self.assertEqual(sender.calls, [])
        self.assertEqual(repo.status_calls[-1]["status"], BuyerNotificationStatus.SKIPPED_NO_EMAIL)

    def test_noops_when_notification_already_claimed(self) -> None:
        repo = FakeDocumentsRepository(_authorized_document(), begin_result=False)
        reader = FakeAttachmentReader()
        sender = FakeEmailSender()

        SendDocumentToBuyerUseCase(repo, reader, sender).execute(
            tenant_id="tenant-1", document_id="doc-1"
        )

        self.assertEqual(reader.calls, [])
        self.assertEqual(sender.calls, [])
        self.assertEqual(repo.status_calls, [])

    def test_marks_failed_and_raises_when_attachment_read_fails(self) -> None:
        repo = FakeDocumentsRepository(_authorized_document())
        reader = FakeAttachmentReader(should_fail=True)
        sender = FakeEmailSender()

        with self.assertRaises(InternalError):
            SendDocumentToBuyerUseCase(repo, reader, sender).execute(
                tenant_id="tenant-1", document_id="doc-1"
            )

        self.assertEqual(sender.calls, [])
        self.assertEqual(repo.status_calls[-1]["status"], BuyerNotificationStatus.FAILED)

    def test_marks_failed_and_raises_when_email_fails(self) -> None:
        repo = FakeDocumentsRepository(_authorized_document())
        reader = FakeAttachmentReader()
        sender = FakeEmailSender(should_fail=True)

        with self.assertRaises(InternalError):
            SendDocumentToBuyerUseCase(repo, reader, sender).execute(
                tenant_id="tenant-1", document_id="doc-1"
            )

        self.assertEqual(repo.status_calls[-1]["status"], BuyerNotificationStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
