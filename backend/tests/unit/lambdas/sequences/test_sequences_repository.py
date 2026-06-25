from __future__ import annotations

import unittest

from botocore.exceptions import ClientError

from lambdas.sequences.domain.errors import SequenceExhaustedError
from lambdas.sequences.infra.sequences_repository import DynamoSequencesRepository
from shared.errors import DatabaseError
from tests.unit.support import configure_unit_environment

configure_unit_environment()


class FakeSequencesTable:
    def __init__(self, *, put_error_code: str | None = None) -> None:
        self.put_calls: list[dict] = []
        self.update_calls: list[dict] = []
        self._put_error_code = put_error_code

    def put_item(self, **kwargs) -> dict:
        self.put_calls.append(kwargs)
        if self._put_error_code:
            raise ClientError(
                {"Error": {"Code": self._put_error_code, "Message": "boom"}}, "PutItem"
            )
        return {}

    def update_item(self, **kwargs) -> dict:
        self.update_calls.append(kwargs)
        return {"Attributes": {"current": 1}}


class SeqSkTests(unittest.TestCase):
    def test_doc_type_01_has_no_suffix(self) -> None:
        repo = DynamoSequencesRepository(FakeSequencesTable())
        self.assertEqual(repo._seq_sk("001", "099"), "SEQ#001#099")
        self.assertEqual(repo._seq_sk("001", "099", "01"), "SEQ#001#099")

    def test_other_doc_type_has_suffix(self) -> None:
        repo = DynamoSequencesRepository(FakeSequencesTable())
        self.assertEqual(repo._seq_sk("001", "099", "04"), "SEQ#001#099#04")


class ReserveNextTests(unittest.TestCase):
    def test_doc_type_01_does_not_lazy_create(self) -> None:
        table = FakeSequencesTable()
        repo = DynamoSequencesRepository(table)

        repo.reserve_next("tenant-1", "001099")

        self.assertEqual(table.put_calls, [])
        self.assertEqual(len(table.update_calls), 1)
        self.assertEqual(table.update_calls[0]["Key"]["sk"], "SEQ#001#099")

    def test_other_doc_type_lazy_creates_before_incrementing(self) -> None:
        table = FakeSequencesTable()
        repo = DynamoSequencesRepository(table)

        repo.reserve_next("tenant-1", "001099", doc_type="04")

        self.assertEqual(len(table.put_calls), 1)
        put_item = table.put_calls[0]["Item"]
        self.assertEqual(put_item["sk"], "SEQ#001#099#04")
        self.assertEqual(put_item["current"], 0)
        self.assertEqual(put_item["initial"], 1)
        self.assertEqual(table.update_calls[0]["Key"]["sk"], "SEQ#001#099#04")

    def test_other_doc_type_swallows_already_exists_on_lazy_create(self) -> None:
        table = FakeSequencesTable(put_error_code="ConditionalCheckFailedException")
        repo = DynamoSequencesRepository(table)

        result = repo.reserve_next("tenant-1", "001099", doc_type="04")

        self.assertEqual(result, 1)
        self.assertEqual(len(table.update_calls), 1)

    def test_other_doc_type_raises_database_error_on_unexpected_put_failure(self) -> None:
        table = FakeSequencesTable(put_error_code="InternalServerError")
        repo = DynamoSequencesRepository(table)

        with self.assertRaises(DatabaseError):
            repo.reserve_next("tenant-1", "001099", doc_type="04")

    def test_exhausted_counter_raises(self) -> None:
        class ExhaustedTable(FakeSequencesTable):
            def update_item(self, **kwargs) -> dict:
                self.update_calls.append(kwargs)
                raise ClientError(
                    {"Error": {"Code": "ConditionalCheckFailedException", "Message": "boom"}},
                    "UpdateItem",
                )

        repo = DynamoSequencesRepository(ExhaustedTable())
        with self.assertRaises(SequenceExhaustedError):
            repo.reserve_next("tenant-1", "001099")


if __name__ == "__main__":
    unittest.main()
