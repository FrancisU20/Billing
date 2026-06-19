from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from lambdas.products.domain.commands import CreateProductCommand, UpdateProductCommand
from lambdas.products.domain.enums import ProductKind, ProductStatus
from shared.dates import isoformat_ecuador
from shared.domain.base_entity import TenantScopedEntity
from shared.errors import ValidationError

_SKU_RE = re.compile(r"^[A-Z0-9][A-Z0-9._\-/]{0,31}$")
_UNIT_RE = re.compile(r"^[a-z][a-z0-9_/-]{0,24}$")
_VALID_IVA_RATES = {"15", "5", "0", "EXENTO"}


@dataclass
class Product(TenantScopedEntity):
    sku: str = ""
    sku_normalized: str = ""
    name: str = ""
    description: str = ""
    kind: ProductKind = ProductKind.PRODUCT
    unit: str = "unit"
    unit_price: Decimal = Decimal("0.00")
    iva_rate: str = "15"
    stock_enabled: bool = False
    stock_quantity: Decimal | None = None
    low_stock_threshold: Decimal | None = None
    status: ProductStatus = ProductStatus.ACTIVE

    @classmethod
    def create(cls, cmd: CreateProductCommand) -> Product:
        sku = _normalize_sku(cmd.sku)
        stock_enabled = bool(cmd.stock_enabled)
        return cls(
            tenant_id=cmd.tenant_id,
            sku=sku,
            sku_normalized=sku,
            name=_required_text(cmd.name, "name", max_length=160),
            description=_optional_text(cmd.description, max_length=500),
            kind=_kind(cmd.kind),
            unit=_unit(cmd.unit),
            unit_price=_money(cmd.unit_price),
            iva_rate=_iva_rate(cmd.iva_rate),
            stock_enabled=stock_enabled,
            stock_quantity=_stock_quantity(cmd.stock_quantity, stock_enabled),
            low_stock_threshold=_optional_non_negative(cmd.low_stock_threshold),
            status=ProductStatus.ACTIVE,
            created_by=cmd.created_by,
            updated_by=cmd.created_by,
        )

    def update(self, cmd: UpdateProductCommand) -> None:
        if cmd.sku is not None:
            self.sku = _normalize_sku(cmd.sku)
            self.sku_normalized = self.sku
        if cmd.name is not None:
            self.name = _required_text(cmd.name, "name", max_length=160)
        if cmd.description is not None:
            self.description = _optional_text(cmd.description, max_length=500)
        if cmd.kind is not None:
            self.kind = _kind(cmd.kind)
        if cmd.unit is not None:
            self.unit = _unit(cmd.unit)
        if cmd.unit_price is not None:
            self.unit_price = _money(cmd.unit_price)
        if cmd.iva_rate is not None:
            self.iva_rate = _iva_rate(cmd.iva_rate)
        if cmd.stock_enabled is not None:
            self.stock_enabled = bool(cmd.stock_enabled)
            if not self.stock_enabled:
                self.stock_quantity = None
                self.low_stock_threshold = None
        if cmd.stock_quantity is not None:
            self.stock_quantity = _stock_quantity(cmd.stock_quantity, self.stock_enabled)
        if cmd.low_stock_threshold is not None:
            self.low_stock_threshold = _optional_non_negative(cmd.low_stock_threshold)
        if cmd.status is not None:
            try:
                self.status = ProductStatus(cmd.status)
            except ValueError as exc:
                raise ValidationError("Estado de producto inválido") from exc
        self.touch(cmd.updated_by)

    def delete(self, user_id: str) -> None:
        self.soft_delete(user_id)

    def to_invoice_snapshot(self) -> dict:
        return {
            "product_id": self.id,
            "code": self.sku,
            "description": self.description or self.name,
            "unit_price": str(self.unit_price),
            "iva_rate": self.iva_rate,
        }

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "kind": self.kind.value,
            "unit": self.unit,
            "unit_price": str(self.unit_price),
            "iva_rate": self.iva_rate,
            "stock_enabled": self.stock_enabled,
            "stock_quantity": str(self.stock_quantity) if self.stock_quantity is not None else None,
            "low_stock_threshold": (
                str(self.low_stock_threshold) if self.low_stock_threshold is not None else None
            ),
            "status": self.status.value,
            "created_at": isoformat_ecuador(self.created_at),
            "updated_at": isoformat_ecuador(self.updated_at),
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "version": self.version,
        }


def _normalize_sku(value: str) -> str:
    sku = (value or "").strip().upper()
    if not _SKU_RE.match(sku):
        raise ValidationError("SKU inválido")
    return sku


def _required_text(value: str, field_name: str, *, max_length: int) -> str:
    text = (value or "").strip()
    if not text:
        raise ValidationError(f"{field_name} es requerido")
    if len(text) > max_length:
        raise ValidationError(f"{field_name} excede el máximo permitido")
    return text


def _optional_text(value: str, *, max_length: int) -> str:
    text = (value or "").strip()
    if len(text) > max_length:
        raise ValidationError("Texto excede el máximo permitido")
    return text


def _kind(value: str) -> ProductKind:
    try:
        return ProductKind(value)
    except ValueError as exc:
        raise ValidationError("Tipo de producto inválido") from exc


def _unit(value: str) -> str:
    unit = (value or "unit").strip().lower()
    if not _UNIT_RE.match(unit):
        raise ValidationError("Unidad inválida")
    return unit


def _money(value: Decimal) -> Decimal:
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    if amount < 0:
        raise ValidationError("El precio no puede ser negativo")
    return amount


def _iva_rate(value: str) -> str:
    if value not in _VALID_IVA_RATES:
        raise ValidationError("Tarifa IVA inválida")
    return value


def _stock_quantity(value: Decimal | None, stock_enabled: bool) -> Decimal | None:
    if not stock_enabled:
        return None
    quantity = Decimal("0") if value is None else Decimal(str(value)).quantize(Decimal("0.01"))
    if quantity < 0:
        raise ValidationError("El stock no puede ser negativo")
    return quantity


def _optional_non_negative(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    quantity = Decimal(str(value)).quantize(Decimal("0.01"))
    if quantity < 0:
        raise ValidationError("El umbral de stock no puede ser negativo")
    return quantity
