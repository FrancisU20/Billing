from __future__ import annotations

from pydantic import BaseModel, Field


class CreatePaymentRequest(BaseModel):
    plan_id: str = Field(..., min_length=1)
    currency: str = Field("USD", pattern=r"^[A-Z]{3}$")


class ConfirmPaymentRequest(BaseModel):
    card_token: str = Field(..., min_length=1)
    client_first_name: str = Field(..., min_length=1)
    client_last_name: str = Field(..., min_length=1)
    client_email: str = Field(..., min_length=1)
    client_document_type: str = Field(..., pattern=r"^(CI|RUC)$")
    client_document: str = Field(..., min_length=1)
