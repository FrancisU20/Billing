from __future__ import annotations

from pydantic import BaseModel, Field


class CreatePaymentRequest(BaseModel):
    plan_id: str = Field(..., min_length=1)
    currency: str = Field("USD", pattern=r"^[A-Z]{3}$")
