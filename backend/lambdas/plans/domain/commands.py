from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CreatePlanCommand:
    slug: str  # immutable — not in UpdatePlanCommand
    name: str
    description: str
    monthly_price: Decimal
    annual_price: Decimal
    document_limit: int
    limit_cycle: str
    max_locations: int
    max_emission_points: int
    max_users: int
    pruebas_monthly_docs_limit: int
    pruebas_monthly_bulk_limit: int
    dedicated_queue: bool
    self_service: bool
    includes_credit_notes: bool
    includes_withholdings: bool
    includes_delivery_notes: bool
    includes_api: bool
    order: int
    created_by: str


@dataclass
class UpdatePlanCommand:
    id: str  # plan UUID
    updated_by: str
    # slug is immutable — cannot be updated
    name: str | None = None
    description: str | None = None
    monthly_price: Decimal | None = None
    annual_price: Decimal | None = None
    document_limit: int | None = None
    limit_cycle: str | None = None
    max_locations: int | None = None
    max_emission_points: int | None = None
    max_users: int | None = None
    pruebas_monthly_docs_limit: int | None = None
    pruebas_monthly_bulk_limit: int | None = None
    dedicated_queue: bool | None = None
    self_service: bool | None = None
    includes_credit_notes: bool | None = None
    includes_withholdings: bool | None = None
    includes_delivery_notes: bool | None = None
    includes_api: bool | None = None
    order: int | None = None


@dataclass
class TogglePlanCommand:
    id: str  # plan UUID
    active: bool
    updated_by: str
