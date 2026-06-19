from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CreateProductCommand:
    tenant_id: str
    sku: str
    name: str
    unit_price: Decimal
    iva_rate: str
    created_by: str
    description: str = ""
    kind: str = "PRODUCT"
    unit: str = "unit"
    discount_percentage: Decimal | None = None
    stock_enabled: bool = False
    stock_quantity: Decimal | None = None
    low_stock_threshold: Decimal | None = None


@dataclass(frozen=True)
class UpdateProductCommand:
    product_id: str
    updated_by: str
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    kind: str | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    iva_rate: str | None = None
    discount_percentage: Decimal | None = None
    stock_enabled: bool | None = None
    stock_quantity: Decimal | None = None
    low_stock_threshold: Decimal | None = None
    status: str | None = None
