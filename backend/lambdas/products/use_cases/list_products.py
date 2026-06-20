from __future__ import annotations

from dataclasses import dataclass

from lambdas.products.domain.entity import Product
from lambdas.products.domain.repositories.i_product_repository import IProductRepository


@dataclass(frozen=True)
class ListProductsQuery:
    limit: int
    next_token: str | None = None
    status: str | None = None
    kind: str | None = None
    q: str | None = None
    sku: str | None = None


class ListProductsUseCase:
    def __init__(self, repo: IProductRepository) -> None:
        self._repo = repo

    def execute(self, query: ListProductsQuery) -> tuple[list[Product], str | None]:
        return self._repo.list(
            limit=query.limit,
            next_token=query.next_token,
            status=query.status,
            kind=query.kind,
            q=query.q,
            sku=query.sku,
        )

    def count(self, query: ListProductsQuery) -> int | None:
        """None when `q`/`sku` are active — those filters are matched in Python."""
        if query.q or query.sku:
            return None
        return self._repo.count(status=query.status, kind=query.kind)
