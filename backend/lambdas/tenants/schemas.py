"""
Schemas Pydantic para el Lambda de tenants.

Solo validan estructura HTTP (campos requeridos, tipos, longitudes).
La validación de negocio (RUC válido, email válido) ocurre en la entidad Tenant.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class CreateTenantRequest(BaseModel):
    ruc:              str = Field(..., min_length=10, max_length=13)
    nombre_comercial: str = Field(..., min_length=2,  max_length=200)
    nombre_rep_legal: str = Field(..., min_length=2,  max_length=200)
    email:            str = Field(..., min_length=5,  max_length=200)
    telefono:         str = Field(..., min_length=7,  max_length=20)
    direccion:        str = Field(..., min_length=5,  max_length=500)
    plan:             str = Field("basico", max_length=50)


class UpdateTenantRequest(BaseModel):
    nombre_comercial: str | None = Field(None, min_length=2, max_length=200)
    nombre_rep_legal: str | None = Field(None, min_length=2, max_length=200)
    email:            str | None = Field(None, min_length=5, max_length=200)
    telefono:         str | None = Field(None, min_length=7, max_length=20)
    direccion:        str | None = Field(None, min_length=5, max_length=500)
    ambiente_sri:     str | None = Field(None, pattern="^(pruebas|produccion)$")


class ToggleStatusRequest(BaseModel):
    estado: str = Field(..., pattern="^(activo|suspendido|inactivo)$")
