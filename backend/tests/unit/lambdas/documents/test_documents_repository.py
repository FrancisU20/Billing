from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from botocore.exceptions import ClientError

from lambdas.documents.domain.entities import Document, DocumentStatus
from lambdas.documents.infra.documents_repository import DynamoDocumentsRepository
from shared.errors import DatabaseError


class FakeDocumentsTable:
    table_name = "unit-documents"

    def __init__(self, error_code: str | None = None) -> None:
        self.error_code = error_code
        self.update_calls: list[dict] = []

    def update_item(self, **kwargs) -> dict:
        self.update_calls.append(kwargs)
        if self.error_code:
            raise ClientError({"Error": {"Code": self.error_code, "Message": "boom"}}, "UpdateItem")
        return {}


class _FakeDynamoClient:
    def __init__(self) -> None:
        self.transact_write_calls: list[dict] = []

    def transact_write_items(self, **kwargs) -> dict:
        self.transact_write_calls.append(kwargs)
        return {}


class _FakeMeta:
    def __init__(self, client: _FakeDynamoClient) -> None:
        self.client = client


class FakeTransactTable:
    table_name = "unit-documents"

    def __init__(self) -> None:
        self.client = _FakeDynamoClient()
        self.meta = _FakeMeta(self.client)


class FakeAuditTable:
    table_name = "unit-audit"


def _make_document(**overrides) -> Document:
    defaults: dict = {
        "document_id": "doc-1",
        "tenant_id": "tenant-1",
        "doc_type": "01",
        "status": DocumentStatus.PENDING,
        "serie": "001001",
        "sequential": 1,
        "access_key": "1" * 49,
        "client_id": None,
        "buyer_id_type": "07",
        "buyer_id": "9999999999999",
        "buyer_name": "Consumidor Final",
        "buyer_email": None,
        "issued_at": date(2026, 6, 18),
        "sri_environment": "testing",
        "subtotal": Decimal("10.00"),
        "total_discount": Decimal("0.00"),
        "iva_15": Decimal("1.50"),
        "iva_5": Decimal("0.00"),
        "iva_0": Decimal("0.00"),
        "total": Decimal("11.50"),
        "payment_method": "01",
        "lines": [],
    }
    defaults.update(overrides)
    return Document(**defaults)


class DynamoDocumentsRepositorySaveTests(unittest.TestCase):
    def test_save_does_not_write_audit_without_override_reason(self) -> None:
        table = FakeTransactTable()
        repo = DynamoDocumentsRepository(table, FakeAuditTable())

        repo.save(_make_document())

        transact_items = table.client.transact_write_calls[0]["TransactItems"]
        self.assertEqual(len(transact_items), 1)

    def test_save_writes_audit_when_override_reason_is_set(self) -> None:
        table = FakeTransactTable()
        repo = DynamoDocumentsRepository(table, FakeAuditTable())

        repo.save(
            _make_document(),
            override_reason="Gesto comercial autorizado",
            user_id="user-1",
        )

        transact_items = table.client.transact_write_calls[0]["TransactItems"]
        self.assertEqual(len(transact_items), 2)
        audit_put = transact_items[1]["Put"]
        self.assertEqual(audit_put["TableName"], "unit-audit")
        self.assertEqual(audit_put["Item"]["action"], "DISCOUNT_CEILING_OVERRIDE")
        self.assertEqual(audit_put["Item"]["changed_by"], "user-1")
        self.assertEqual(audit_put["Item"]["after"]["reason"], "Gesto comercial autorizado")

    def test_save_skips_audit_without_audit_table(self) -> None:
        table = FakeTransactTable()
        repo = DynamoDocumentsRepository(table)

        repo.save(_make_document(), override_reason="Motivo", user_id="user-1")

        transact_items = table.client.transact_write_calls[0]["TransactItems"]
        self.assertEqual(len(transact_items), 1)


class DynamoDocumentsRepositoryUpdateStatusTests(unittest.TestCase):
    def test_transitions_status_and_sets_optional_fields(self) -> None:
        table = FakeDocumentsTable()
        repo = DynamoDocumentsRepository(table)

        result = repo.update_status(
            "tenant-1",
            "doc-1",
            expected_status=DocumentStatus.PENDING,
            new_status=DocumentStatus.PROCESSING,
        )

        self.assertTrue(result)
        self.assertEqual(len(table.update_calls), 1)
        call = table.update_calls[0]
        self.assertEqual(call["ExpressionAttributeValues"][":new_status"], "PROCESSING")
        self.assertEqual(call["ExpressionAttributeValues"][":expected_status"], "PENDING")
        self.assertNotIn("ADD retry_count", call["UpdateExpression"])

    def test_increment_retry_adds_retry_count(self) -> None:
        table = FakeDocumentsTable()
        repo = DynamoDocumentsRepository(table)

        repo.update_status(
            "tenant-1",
            "doc-1",
            expected_status=DocumentStatus.PENDING,
            new_status=DocumentStatus.FAILED,
            increment_retry=True,
        )

        call = table.update_calls[0]
        self.assertIn("ADD retry_count :one", call["UpdateExpression"])
        self.assertEqual(call["ExpressionAttributeValues"][":one"], 1)

    def test_optional_fields_are_included_when_provided(self) -> None:
        table = FakeDocumentsTable()
        repo = DynamoDocumentsRepository(table)

        repo.update_status(
            "tenant-1",
            "doc-1",
            expected_status=DocumentStatus.PROCESSING,
            new_status=DocumentStatus.AUTHORIZED,
            authorization_number="1234567890",
            xml_s3_key="tenants/tenant-1/docs/2026/doc-1.xml",
            ride_s3_key="tenants/tenant-1/docs/2026/doc-1.pdf",
        )

        call = table.update_calls[0]
        self.assertEqual(call["ExpressionAttributeValues"][":authorization_number"], "1234567890")
        self.assertEqual(
            call["ExpressionAttributeValues"][":xml_s3_key"],
            "tenants/tenant-1/docs/2026/doc-1.xml",
        )

    def test_conditional_check_failed_returns_false_without_raising(self) -> None:
        table = FakeDocumentsTable(error_code="ConditionalCheckFailedException")
        repo = DynamoDocumentsRepository(table)

        result = repo.update_status(
            "tenant-1",
            "doc-1",
            expected_status=DocumentStatus.PENDING,
            new_status=DocumentStatus.PROCESSING,
        )

        self.assertFalse(result)

    def test_other_client_errors_raise_database_error(self) -> None:
        table = FakeDocumentsTable(error_code="InternalServerError")
        repo = DynamoDocumentsRepository(table)

        with self.assertRaises(DatabaseError):
            repo.update_status(
                "tenant-1",
                "doc-1",
                expected_status=DocumentStatus.PENDING,
                new_status=DocumentStatus.PROCESSING,
            )


if __name__ == "__main__":
    unittest.main()
