from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class EmitDocumentLineRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=25)
    description: str = Field(..., min_length=1, max_length=300)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)
    iva_rate: Literal["15", "5", "0", "EXENTO"]


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


class ListDocumentsQueryParams(BaseModel):
    status: str | None = None
    serie: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None
