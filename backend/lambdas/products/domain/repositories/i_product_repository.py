from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas.products.domain.entity import Product


class IProductRepository(ABC):
    @abstractmethod
    def get_by_id(self, product_id: str) -> Product:
        """Return one product by stable id."""

    @abstractmethod
    def get_by_sku(self, sku: str, exclude_id: str | None = None) -> Product | None:
        """Return active product by SKU within the tenant."""

    @abstractmethod
    def list(
        self,
        *,
        limit: int,
        next_token: str | None,
        status: str | None = None,
        kind: str | None = None,
        q: str | None = None,
        sku: str | None = None,
    ) -> tuple[list[Product], str | None]:
        """List tenant products."""

    @abstractmethod
    def commit(
        self,
        *,
        product: Product,
        user_id: str,
        action: str,
        idempotency,
        response: dict | None,
    ) -> None:
        """Persist product plus lock/audit/idempotency state."""
