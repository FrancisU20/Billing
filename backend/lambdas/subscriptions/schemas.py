from __future__ import annotations

from pydantic import BaseModel, Field


class CreatePaymentRequest(BaseModel):
    plan_id: str = Field(..., min_length=1)
    currency: str = Field("USD", pattern=r"^[A-Z]{3}$")


class ConfirmPaymentRequest(BaseModel):
    card_token: str = Field(..., min_length=1)
    payer_email: str | None = None
