from __future__ import annotations

import time
import unittest

from shared.audit.writer import audit_item, audit_put_transact_item


class AuditItemTests(unittest.TestCase):
    def _make(self, **kwargs) -> dict:
        defaults = dict(
            pk="AUDIT#tenant-1",
            entity_type="Client",
            entity_id="client-1",
            action="CREATE",
            changed_by="user-x",
            before=None,
            after={"legal_name": "Acme"},
        )
        defaults.update(kwargs)
        return audit_item(**defaults)

    def test_required_fields_present(self) -> None:
        item = self._make()
        for key in (
            "pk",
            "sk",
            "entity_id",
            "entity_type",
            "action",
            "changed_by",
            "before",
            "after",
            "created_at",
            "ttl",
        ):
            self.assertIn(key, item)

    def test_sk_contains_action_and_entity_id(self) -> None:
        item = self._make(action="UPDATE", entity_id="client-1")
        self.assertIn("UPDATE", item["sk"])
        self.assertIn("client-1", item["sk"])

    def test_before_none_becomes_empty_dict(self) -> None:
        item = self._make(before=None)
        self.assertEqual(item["before"], {})

    def test_after_none_becomes_empty_dict(self) -> None:
        item = self._make(after=None)
        self.assertEqual(item["after"], {})

    def test_before_dict_preserved(self) -> None:
        before = {"status": "active"}
        item = self._make(before=before)
        self.assertEqual(item["before"], before)

    def test_ttl_is_int_and_in_future(self) -> None:
        item = self._make()
        self.assertIsInstance(item["ttl"], int)
        self.assertGreater(item["ttl"], int(time.time()))

    def test_ttl_approx_7_years(self) -> None:
        item = self._make()
        seven_years = 7 * 365 * 24 * 60 * 60
        self.assertAlmostEqual(item["ttl"] - int(time.time()), seven_years, delta=5)


class AuditPutTransactItemTests(unittest.TestCase):
    def test_wraps_in_put_with_table_name(self) -> None:
        item = audit_item(
            pk="AUDIT#t1",
            entity_type="Tenant",
            entity_id="t1",
            action="CREATE",
            changed_by="sys",
            before=None,
            after={"name": "Acme"},
        )
        result = audit_put_transact_item("audit-table", item)
        self.assertIn("Put", result)
        self.assertEqual(result["Put"]["TableName"], "audit-table")
        self.assertEqual(result["Put"]["Item"], item)


if __name__ == "__main__":
    unittest.main()
