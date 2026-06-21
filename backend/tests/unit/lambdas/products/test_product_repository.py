from __future__ import annotations

import unittest
from decimal import Decimal

from lambdas.products.domain.entity import Product
from lambdas.products.infra.product_repository import DynamoProductRepository


class ProductItemSerializationTests(unittest.TestCase):
    """`discount_percentage` se perdia en `_to_item`/`_from_item` — el campo se
    actualizaba en memoria y la respuesta del API lo reflejaba (via `to_dict()`), pero
    nunca se persistia en DynamoDB ni se rehidrataba en el siguiente fetch."""

    def setUp(self) -> None:
        self.repo = DynamoProductRepository("tenant-1", table=None)

    def test_to_item_includes_discount_percentage(self) -> None:
        product = Product(tenant_id="tenant-1", sku="SKU-1", discount_percentage=Decimal("12.50"))

        item = self.repo._to_item(product)

        self.assertEqual(item["discount_percentage"], "12.50")

    def test_to_item_keeps_discount_percentage_none(self) -> None:
        product = Product(tenant_id="tenant-1", sku="SKU-1", discount_percentage=None)

        item = self.repo._to_item(product)

        self.assertIsNone(item["discount_percentage"])

    def test_from_item_round_trips_discount_percentage(self) -> None:
        product = Product(tenant_id="tenant-1", sku="SKU-1", discount_percentage=Decimal("12.50"))

        rehydrated = self.repo._from_item(self.repo._to_item(product))

        self.assertEqual(rehydrated.discount_percentage, Decimal("12.50"))

    def test_from_item_defaults_missing_discount_percentage_to_none(self) -> None:
        product = Product(tenant_id="tenant-1", sku="SKU-1", discount_percentage=None)

        rehydrated = self.repo._from_item(self.repo._to_item(product))

        self.assertIsNone(rehydrated.discount_percentage)


if __name__ == "__main__":
    unittest.main()
