from __future__ import annotations

from lambdas.products.domain.entity import Product
from lambdas.products.domain.repositories.i_product_repository import IProductRepository


class GetProductUseCase:
    def __init__(self, repo: IProductRepository) -> None:
        self._repo = repo

    def execute(self, product_id: str) -> Product:
        return self._repo.get_by_id(product_id)
