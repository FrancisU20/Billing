from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CreateEstablishmentCommand:
    tenant_id: str
    code: str
    label: str
    created_by: str


@dataclass
class AddEmissionPointCommand:
    tenant_id: str
    establishment_code: str
    code: str
    label: str
    initial_sequential: int = 1
    created_by: str = ""


@dataclass
class EditEmissionPointCommand:
    tenant_id: str
    establishment_code: str
    code: str
    label: str | None = None
    initial_sequential: int | None = None
    updated_by: str = ""
