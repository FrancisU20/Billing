from __future__ import annotations

from shared.errors import ConflictError, NotFoundError


class ProductNotFoundError(NotFoundError):
    code = "PRODUCT_NOT_FOUND"
    default_message = "El producto o servicio no fue encontrado."


class ProductDuplicateSkuError(ConflictError):
    code = "PRODUCT_DUPLICATE_SKU"
    default_message = "Ya existe un producto o servicio con ese SKU."
