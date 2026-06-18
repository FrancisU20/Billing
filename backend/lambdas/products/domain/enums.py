from __future__ import annotations

from enum import StrEnum


class ProductKind(StrEnum):
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"
    PACKAGE = "PACKAGE"
    MEMBERSHIP = "MEMBERSHIP"
    OTHER = "OTHER"


class ProductStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
