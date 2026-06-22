from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateTenantCommand:
    ruc: str
    trade_name: str
    legal_name: str
    legal_rep_name: str
    email: str
    phone: str
    address: str
    accounting_required: bool
    plan_id: str
    created_by: str
    billing_cycle: str = "month"  # "month" | "year" — elegido en el toggle de precios


@dataclass(frozen=True)
class UpdateTenantCommand:
    tenant_id: str
    updated_by: str
    trade_name: str | None = None
    legal_name: str | None = None
    legal_rep_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    accounting_required: bool | None = None
    sri_environment: str | None = None


@dataclass(frozen=True)
class ToggleStatusCommand:
    tenant_id: str
    new_status: str  # "active" | "suspended" | "inactive"
    updated_by: str


@dataclass(frozen=True)
class RetryTenantOnboardingCommand:
    tenant_id: str
    requested_by: str


@dataclass(frozen=True)
class ChangeTenantPlanCommand:
    tenant_id: str
    plan_id: str
    billing_cycle: str
    updated_by: str
