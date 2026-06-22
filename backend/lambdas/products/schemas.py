from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class CreateProductRequest(BaseModel):
    sku: str = Field(..., min_length=1, max_length=36)
    name: str = Field(..., min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    kind: Literal["PRODUCT", "SERVICE", "PACKAGE", "MEMBERSHIP", "OTHER"] = "PRODUCT"
    unit: str = Field(default="unit", min_length=1, max_length=25)
    unit_price: Decimal = Field(..., ge=0)
    iva_rate: Literal["15", "5", "0", "EXENTO"] = "15"
    discount_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    stock_enabled: bool = False
    stock_quantity: Decimal | None = Field(default=None, ge=0)
    low_stock_threshold: Decimal | None = Field(default=None, ge=0)


class UpdateProductRequest(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=36)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    kind: Literal["PRODUCT", "SERVICE", "PACKAGE", "MEMBERSHIP", "OTHER"] | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=25)
    unit_price: Decimal | None = Field(default=None, ge=0)
    iva_rate: Literal["15", "5", "0", "EXENTO"] | None = None
    discount_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    stock_enabled: bool | None = None
    stock_quantity: Decimal | None = Field(default=None, ge=0)
    low_stock_threshold: Decimal | None = Field(default=None, ge=0)
    status: Literal["ACTIVE", "INACTIVE"] | None = None


class UpdateDiscountCampaignRequest(BaseModel):
    active: bool
    percentage: Decimal = Field(..., ge=0, le=100)
