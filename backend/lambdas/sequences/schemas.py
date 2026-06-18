from __future__ import annotations

from pydantic import BaseModel, Field


class CreateEstablishmentRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=3, pattern=r"^\d{3}$")
    label: str = Field(..., min_length=1, max_length=200)


class AddEmissionPointRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=3, pattern=r"^\d{3}$")
    label: str = Field(..., min_length=1, max_length=200)
    initial_sequential: int = Field(default=1, ge=1, le=999_999_999)


class EditEmissionPointRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    initial_sequential: int | None = Field(default=None, ge=1, le=999_999_999)
