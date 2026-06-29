from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from shared.domain.value_objects.ecuador_identification import is_valid_cedula, is_valid_ruc


class CreatePaymentRequest(BaseModel):
    plan_id: str = Field(..., min_length=1)
    currency: str = Field("USD", pattern=r"^[A-Z]{3}$")
    billing_cycle: str = Field("month", pattern=r"^(month|year)$")


class ConfirmPaymentRequest(BaseModel):
    card_token: str = Field(..., min_length=1)
    client_first_name: str = Field(..., min_length=1)
    client_last_name: str = Field(..., min_length=1)
    client_email: str = Field(..., min_length=1)
    client_document_type: str = Field(..., pattern=r"^(CI|RUC)$")
    client_document: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_ecuadorian_document(self) -> ConfirmPaymentRequest:
        document = self.client_document.strip()
        if self.client_document_type == "CI" and not is_valid_cedula(document):
            raise ValueError("client_document must be a valid Ecuadorian cedula")
        if self.client_document_type == "RUC" and not is_valid_ruc(document):
            raise ValueError("client_document must be a valid Ecuadorian RUC")
        self.client_document = document
        return self
