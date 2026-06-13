from __future__ import annotations

from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    ruc: str = Field(..., min_length=10, max_length=13)
    trade_name: str = Field(..., min_length=2, max_length=200)
    legal_name: str = Field(..., min_length=2, max_length=200)
    legal_rep_name: str = Field(..., min_length=2, max_length=200)
    email: str = Field(..., min_length=5, max_length=200)
    phone: str = Field(..., min_length=7, max_length=20)
    address: str = Field(..., min_length=5, max_length=500)
    accounting_required: bool = False
    plan_id: str = Field(..., min_length=1, max_length=36)
