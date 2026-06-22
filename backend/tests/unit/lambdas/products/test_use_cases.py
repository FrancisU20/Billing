from __future__ import annotations

import unittest
from decimal import Decimal

from lambdas.products.domain.commands import CreateProductCommand, UpdateProductCommand
from lambdas.products.domain.errors import ProductNotFoundError
from lambdas.products.use_cases.create_product import CreateProductUseCase
from lambdas.products.use_cases.delete_product import DeleteProductUseCase
from lambdas.products.use_cases.list_products import ListProductsQuery, ListProductsUseCase
from lambdas.products.use_cases.update_product import UpdateProductUseCase
from shared.errors import ValidationError


class FakeProductRepository:
    def __init__(self) -> None:
        self.products = {}
        self.list_calls: list[dict] = []
        self.list_result = ([], None)
        self.commit_calls: list[dict] = []
        self.count_calls: list[dict] = []
        self.count_result = 0

    def get_by_id(self, product_id):
        product = self.products.get(product_id)
        if product is None:
            raise ProductNotFoundError()
        return product

    def get_by_sku(self, sku, exclude_id=None):
        return None

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return self.list_result

    def count(self, **kwargs):
        self.count_calls.append(kwargs)
        return self.count_result

    def commit(self, **kwargs):
        self.commit_calls.append(kwargs)


def _create_cmd(**overrides):
    defaults = dict(
        tenant_id="tenant-1",
        sku="serv-001",
        name="Servicio mensual",
        description="Servicio mensual de soporte",
        kind="SERVICE",
        unit="month",
        unit_price=Decimal("25.50"),
        iva_rate="15",
        stock_enabled=False,
        created_by="user-1",
    )
    defaults.update(overrides)
    return CreateProductCommand(**defaults)


class ProductUseCaseTests(unittest.TestCase):
    def test_create_normalizes_sku_and_decimal_price(self) -> None:
        repo = FakeProductRepository()
        product = CreateProductUseCase(repo).execute(_create_cmd(sku=" serv-001 "))

        self.assertEqual(product.sku, "SERV-001")
        self.assertEqual(product.unit_price, Decimal("25.50"))
        self.assertEqual(product.kind.value, "SERVICE")
        self.assertEqual(repo.commit_calls, [])

    def test_create_accepts_uuid_sku(self) -> None:
        repo = FakeProductRepository()
        product = CreateProductUseCase(repo).execute(
            _create_cmd(sku="550e8400-e29b-41d4-a716-446655440000")
        )

        self.assertEqual(product.sku, "550E8400-E29B-41D4-A716-446655440000")

    def test_create_rejects_invalid_sku(self) -> None:
        with self.assertRaises(ValidationError):
            CreateProductUseCase(FakeProductRepository()).execute(_create_cmd(sku="*bad*"))

    def test_update_changes_sku_price_and_stock(self) -> None:
        repo = FakeProductRepository()
        product = CreateProductUseCase(repo).execute(_create_cmd())
        repo.products[product.id] = product

        updated = UpdateProductUseCase(repo).execute(
            UpdateProductCommand(
                product_id=product.id,
                updated_by="user-2",
                sku="prod-002",
                kind="PRODUCT",
                unit_price=Decimal("10"),
                stock_enabled=True,
                stock_quantity=Decimal("5"),
            )
        )

        self.assertEqual(updated.sku, "PROD-002")
        self.assertEqual(updated.kind.value, "PRODUCT")
        self.assertEqual(updated.stock_quantity, Decimal("5.00"))

    def test_create_accepts_discount_percentage(self) -> None:
        repo = FakeProductRepository()
        product = CreateProductUseCase(repo).execute(
            _create_cmd(discount_percentage=Decimal("15.5"))
        )

        self.assertEqual(product.discount_percentage, Decimal("15.50"))

    def test_create_defaults_discount_percentage_to_none(self) -> None:
        repo = FakeProductRepository()
        product = CreateProductUseCase(repo).execute(_create_cmd())

        self.assertIsNone(product.discount_percentage)

    def test_create_rejects_discount_percentage_above_100(self) -> None:
        with self.assertRaises(ValidationError):
            CreateProductUseCase(FakeProductRepository()).execute(
                _create_cmd(discount_percentage=Decimal("100.01"))
            )

    def test_create_rejects_negative_discount_percentage(self) -> None:
        with self.assertRaises(ValidationError):
            CreateProductUseCase(FakeProductRepository()).execute(
                _create_cmd(discount_percentage=Decimal("-1"))
            )

    def test_update_changes_discount_percentage(self) -> None:
        repo = FakeProductRepository()
        product = CreateProductUseCase(repo).execute(_create_cmd())
        repo.products[product.id] = product

        updated = UpdateProductUseCase(repo).execute(
            UpdateProductCommand(
                product_id=product.id,
                updated_by="user-2",
                discount_percentage=Decimal("60"),
            )
        )

        self.assertEqual(updated.discount_percentage, Decimal("60.00"))

    def test_delete_soft_deletes(self) -> None:
        repo = FakeProductRepository()
        product = CreateProductUseCase(repo).execute(_create_cmd())
        repo.products[product.id] = product

        deleted = DeleteProductUseCase(repo).execute(product.id, "user-2")

        self.assertTrue(deleted.deleted)
        self.assertEqual(deleted.deleted_by, "user-2")

    def test_list_delegates_to_repository(self) -> None:
        repo = FakeProductRepository()
        expected = CreateProductUseCase(repo).execute(_create_cmd())
        repo.list_result = ([expected], "cursor-1")

        products, next_token = ListProductsUseCase(repo).execute(
            ListProductsQuery(
                limit=10,
                next_token="cursor-0",
                status="ACTIVE",
                kind="SERVICE",
                q="soporte",
                sku="SERV-001",
            )
        )

        self.assertEqual(products, [expected])
        self.assertEqual(next_token, "cursor-1")
        self.assertEqual(repo.list_calls[0]["kind"], "SERVICE")
        self.assertEqual(repo.list_calls[0]["sku"], "SERV-001")

    def test_count_delegates_to_repository_without_text_filters(self) -> None:
        repo = FakeProductRepository()
        repo.count_result = 9

        total = ListProductsUseCase(repo).count(ListProductsQuery(limit=10, status="ACTIVE"))

        self.assertEqual(total, 9)
        self.assertEqual(repo.count_calls[0]["status"], "ACTIVE")

    def test_count_is_none_when_q_or_sku_filter_is_active(self) -> None:
        repo = FakeProductRepository()
        repo.count_result = 9

        self.assertIsNone(ListProductsUseCase(repo).count(ListProductsQuery(limit=10, q="x")))
        self.assertIsNone(ListProductsUseCase(repo).count(ListProductsQuery(limit=10, sku="X")))
        self.assertEqual(repo.count_calls, [])


if __name__ == "__main__":
    unittest.main()
