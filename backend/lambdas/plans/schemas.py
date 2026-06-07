from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class CreatePlanRequest(BaseModel):
    slug:                str   = Field(..., pattern=r"^[a-z0-9_-]{2,30}$")
    name:                str   = Field(..., min_length=2, max_length=80)
    description:         str   = Field("", max_length=300)
    monthly_price:       Decimal = Field(Decimal("0.00"), ge=0)
    annual_price:        Decimal = Field(Decimal("0.00"), ge=0)
    document_limit:      int   = Field(..., ge=-1)
    limit_cycle:         str   = Field("month", pattern=r"^(month|year)$")
    max_locations:       int   = Field(1, ge=-1)
    max_emission_points: int   = Field(1, ge=-1)
    max_users:           int   = Field(1, ge=-1)
    includes_credit_notes:   bool = True
    includes_withholdings:   bool = True
    includes_delivery_notes: bool = True
    includes_api:            bool = False
    order:               int   = Field(0, ge=0)


class UpdatePlanRequest(BaseModel):
    # slug is not here — it is immutable
    name:                str   | None = Field(None, min_length=2, max_length=80)
    description:         str   | None = Field(None, max_length=300)
    monthly_price:       Decimal | None = Field(None, ge=0)
    annual_price:        Decimal | None = Field(None, ge=0)
    document_limit:      int   | None = Field(None, ge=-1)
    limit_cycle:         str   | None = Field(None, pattern=r"^(month|year)$")
    max_locations:       int   | None = Field(None, ge=-1)
    max_emission_points: int   | None = Field(None, ge=-1)
    max_users:           int   | None = Field(None, ge=-1)
    includes_credit_notes:   bool | None = None
    includes_withholdings:   bool | None = None
    includes_delivery_notes: bool | None = None
    includes_api:            bool | None = None
    order:               int   | None = Field(None, ge=0)


class TogglePlanRequest(BaseModel):
    active: bool
