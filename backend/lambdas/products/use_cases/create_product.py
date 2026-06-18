from __future__ import annotations

from lambdas.products.domain.commands import CreateProductCommand
from lambdas.products.domain.entity import Product
from lambdas.products.domain.repositories.i_product_repository import IProductRepository


class CreateProductUseCase:
    def __init__(self, repo: IProductRepository) -> None:
        self._repo = repo

    def execute(self, cmd: CreateProductCommand) -> Product:
        return Product.create(cmd)
