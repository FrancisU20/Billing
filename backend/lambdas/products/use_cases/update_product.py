from __future__ import annotations

from lambdas.products.domain.commands import UpdateProductCommand
from lambdas.products.domain.entity import Product
from lambdas.products.domain.repositories.i_product_repository import IProductRepository


class UpdateProductUseCase:
    def __init__(self, repo: IProductRepository) -> None:
        self._repo = repo

    def execute(self, cmd: UpdateProductCommand) -> Product:
        product = self._repo.get_by_id(cmd.product_id)
        product.update(cmd)
        return product
