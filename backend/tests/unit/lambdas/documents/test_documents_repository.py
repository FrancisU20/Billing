from __future__ import annotations

import unittest

from botocore.exceptions import ClientError

from lambdas.documents.domain.entities import DocumentStatus
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
