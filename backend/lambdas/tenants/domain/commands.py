from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateTenantCommand:
    ruc: str
    trade_name: str
    legal_rep_name: str
    email: str
    phone: str
    address: str
    plan_id: str
    created_by: str


@dataclass(frozen=True)
class UpdateTenantCommand:
    tenant_id: str
    updated_by: str
    trade_name: str | None = None
    legal_rep_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    sri_environment: str | None = None


@dataclass(frozen=True)
class ToggleStatusCommand:
    tenant_id: str
    new_status: str  # "active" | "suspended" | "inactive"
    updated_by: str
