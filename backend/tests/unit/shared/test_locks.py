from __future__ import annotations

import unittest
from datetime import UTC, datetime

from shared.db.locks import (
    delete_unique_lock_transact_item,
    put_unique_lock_transact_item,
    unique_lock_item,
)


class UniqueLockHelpersTests(unittest.TestCase):
    def test_unique_lock_item_builds_global_lock(self) -> None:
        created_at = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)

        item = unique_lock_item(
            key={"id": "RUC#1790012345001"},
            entity_type="TENANT_RUC_LOCK",
            owner_field="tenant_id",
            owner_id="tenant-1",
            locked_field="locked_ruc",
            locked_value="1790012345001",
            created_at=created_at,
            created_by="user-1",
        )

        self.assertEqual(
            item,
            {
                "id": "RUC#1790012345001",
                "entity_type": "TENANT_RUC_LOCK",
                "tenant_id": "tenant-1",
                "locked_ruc": "1790012345001",
                "created_at": "2026-06-29T12:00:00+00:00",
                "created_by": "user-1",
            },
        )

    def test_unique_lock_item_builds_tenant_scoped_lock(self) -> None:
        item = unique_lock_item(
            key={"pk": "TENANT#tenant-1", "sk": "PRODUCT_SKU#ABC"},
            entity_type="PRODUCT_SKU_LOCK",
            owner_field="product_id",
            owner_id="product-1",
            locked_field="locked_sku",
            locked_value="ABC",
            created_at="2026-06-29T12:00:00+00:00",
            created_by="user-1",
        )

        self.assertEqual(item["pk"], "TENANT#tenant-1")
        self.assertEqual(item["sk"], "PRODUCT_SKU#ABC")
        self.assertEqual(item["product_id"], "product-1")
        self.assertEqual(item["locked_sku"], "ABC")

    def test_put_unique_lock_transact_item_uses_attribute_not_exists(self) -> None:
        transact_item = put_unique_lock_transact_item(
            table_name="table",
            item={"pk": "TENANT#1", "sk": "LOCK#A"},
            partition_key_name="pk",
        )

        self.assertEqual(transact_item["Put"]["TableName"], "table")
        self.assertEqual(
            transact_item["Put"]["ConditionExpression"], "attribute_not_exists(#lock_pk)"
        )
        self.assertEqual(transact_item["Put"]["ExpressionAttributeNames"], {"#lock_pk": "pk"})

    def test_delete_unique_lock_transact_item_allows_missing_or_owned_lock(self) -> None:
        transact_item = delete_unique_lock_transact_item(
            table_name="table",
            key={"pk": "TENANT#1", "sk": "LOCK#A"},
            partition_key_name="pk",
            owner_field="product_id",
            owner_id="product-1",
        )

        self.assertEqual(
            transact_item["Delete"]["ConditionExpression"],
            "attribute_not_exists(#lock_pk) OR #owner_id = :owner_id",
        )
        self.assertEqual(
            transact_item["Delete"]["ExpressionAttributeNames"],
            {"#lock_pk": "pk", "#owner_id": "product_id"},
        )
        self.assertEqual(
            transact_item["Delete"]["ExpressionAttributeValues"],
            {":owner_id": "product-1"},
        )


if __name__ == "__main__":
    unittest.main()
