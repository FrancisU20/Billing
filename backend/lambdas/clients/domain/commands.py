from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AddressCommand:
    label: str
    line: str
    city: str = ""


@dataclass(frozen=True)
class CreateClientCommand:
    tenant_id: str
    identification: str
    identification_type: str
    person_type: str
    legal_name: str
    created_by: str
    trade_name: str = ""
    special_taxpayer: bool = False
    emails: list[str] | None = None
    phones: list[str] | None = None
    addresses: list[AddressCommand] | None = None


@dataclass(frozen=True)
class UpdateClientCommand:
    client_id: str
    updated_by: str
    identification: str | None = None
    identification_type: str | None = None
    person_type: str | None = None
    legal_name: str | None = None
    trade_name: str | None = None
    special_taxpayer: bool | None = None
    emails: list[str] | None = None
    phones: list[str] | None = None
    addresses: list[AddressCommand] | None = None
    status: str | None = None
