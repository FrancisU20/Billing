from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

_CONSUMIDOR_FINAL_ID_TYPE = "07"
_CONSUMIDOR_FINAL_ID = "9999999999999"
_CONSUMIDOR_FINAL_NAME = "Consumidor Final"


class EmitDocumentLineRequest(BaseModel):
    product_id: str | None = None
    code: str = Field(..., min_length=1, max_length=25)
    description: str = Field(..., min_length=1, max_length=300)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)
    iva_rate: Literal["15", "5", "0", "EXENTO"]

    @model_validator(mode="after")
    def validate_amounts(self) -> EmitDocumentLineRequest:
        gross = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        if gross <= 0:
            raise ValueError("La línea debe tener cantidad y precio mayor a cero.")
        if self.discount > gross:
            raise ValueError("El descuento no puede superar el subtotal bruto de la línea.")
        return self


class EmitDocumentRequest(BaseModel):
    establishment_code: str = Field(..., min_length=3, max_length=3, pattern=r"^\d{3}$")
    emission_point_code: str = Field(..., min_length=3, max_length=3, pattern=r"^\d{3}$")
    doc_type: Literal["01"] = "01"
    issued_at: date
    client_id: str | None = None
    buyer_id_type: Literal["04", "05", "06", "07", "08"]
    buyer_id: str = Field(..., min_length=5, max_length=20)
    buyer_name: str = Field(..., min_length=1, max_length=300)
    buyer_email: str | None = None
    payment_method: Literal["01", "15", "16", "17", "18", "19", "20", "21"] = "01"
    lines: list[EmitDocumentLineRequest] = Field(..., min_length=1)
    override_discount_ceiling: bool = False
    override_reason: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_override(self) -> EmitDocumentRequest:
        if self.override_discount_ceiling and not (self.override_reason or "").strip():
            raise ValueError("Debes indicar el motivo para anular el techo de descuento.")
        return self

    @model_validator(mode="after")
    def normalize_buyer(self) -> EmitDocumentRequest:
        if self.buyer_id_type == _CONSUMIDOR_FINAL_ID_TYPE:
            self.client_id = None
            self.buyer_id = _CONSUMIDOR_FINAL_ID
            self.buyer_name = _CONSUMIDOR_FINAL_NAME
            self.buyer_email = None
            return self

        if self.buyer_id.strip() == _CONSUMIDOR_FINAL_ID:
            raise ValueError("Consumidor Final debe usar tipo de identificación 07.")
        return self


class ListDocumentsQueryParams(BaseModel):
    status: str | None = None
    serie: str | None = None
    q: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None
