from __future__ import annotations

"""Local adapter from documents lambda to products table."""

from lambdas.documents.domain.repositories.i_product_catalog import InvoiceProductSnapshot
from lambdas.products.domain.enums import ProductStatus
from lambdas.products.domain.errors import ProductNotFoundError
from lambdas.products.infra.product_repository import DynamoProductRepository


class DynamoProductCatalog:
    def __init__(self, tenant_id: str, table) -> None:
        self._repo = DynamoProductRepository(tenant_id, table)

    def get_active_snapshot(self, product_id: str) -> InvoiceProductSnapshot:
        product = self._repo.get_by_id(product_id)
        if product.status != ProductStatus.ACTIVE:
            raise ProductNotFoundError()
        snapshot = product.to_invoice_snapshot()
        return InvoiceProductSnapshot(
            product_id=snapshot["product_id"],
            code=snapshot["code"],
            description=snapshot["description"],
            unit_price=product.unit_price,
            iva_rate=snapshot["iva_rate"],
            discount_percentage=product.discount_percentage,
        )
