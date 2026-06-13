from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterTenantCommand:
    ruc: str
    trade_name: str
    legal_name: str
    legal_rep_name: str
    email: str
    phone: str
    address: str
    accounting_required: bool
    plan_id: str
