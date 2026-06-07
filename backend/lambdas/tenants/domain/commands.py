from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateTenantCommand:
    ruc:              str
    nombre_comercial: str
    nombre_rep_legal: str
    email:            str
    telefono:         str
    direccion:        str
    created_by:       str
    plan:             str = "basico"


@dataclass(frozen=True)
class UpdateTenantCommand:
    tenant_id:        str
    updated_by:       str
    nombre_comercial: str | None = None
    nombre_rep_legal: str | None = None
    email:            str | None = None
    telefono:         str | None = None
    direccion:        str | None = None
    ambiente_sri:     str | None = None


@dataclass(frozen=True)
class ToggleStatusCommand:
    tenant_id:  str
    nuevo_estado: str   # "activo" | "suspendido" | "inactivo"
    updated_by: str
