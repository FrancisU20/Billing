from __future__ import annotations

from pydantic import BaseModel, Field


class AddressRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=50)
    line: str = Field(..., min_length=1, max_length=500)
    city: str = Field("", max_length=100)


class CreateClientRequest(BaseModel):
    identification: str = Field(..., min_length=3, max_length=25)
    identification_type: str = Field(..., pattern="^(ruc|cedula|pasaporte|exterior)$")
    person_type: str = Field(..., pattern="^(natural|juridica)$")
    legal_name: str = Field(..., min_length=2, max_length=250)
    trade_name: str = Field("", max_length=250)
    special_taxpayer: bool = False
    emails: list[str] = Field(default_factory=list, max_length=5)
    phones: list[str] = Field(default_factory=list, max_length=5)
    addresses: list[AddressRequest] = Field(default_factory=list, max_length=5)


class UpdateClientRequest(BaseModel):
    identification: str | None = Field(None, min_length=3, max_length=25)
    identification_type: str | None = Field(None, pattern="^(ruc|cedula|pasaporte|exterior)$")
    person_type: str | None = Field(None, pattern="^(natural|juridica)$")
    legal_name: str | None = Field(None, min_length=2, max_length=250)
    trade_name: str | None = Field(None, max_length=250)
    special_taxpayer: bool | None = None
    emails: list[str] | None = Field(None, max_length=5)
    phones: list[str] | None = Field(None, max_length=5)
    addresses: list[AddressRequest] | None = Field(None, max_length=5)
    status: str | None = Field(None, pattern="^(active|inactive)$")
